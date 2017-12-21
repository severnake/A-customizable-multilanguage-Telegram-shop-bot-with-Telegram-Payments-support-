import threading
import typing
import telegram
import strings
import configloader
import sys
import queue as queuem
import database as db

class StopSignal:
    """A data class that should be sent to the worker when the conversation has to be stopped abnormally."""

    def __init__(self, reason: str=""):
        self.reason = reason


class ChatWorker(threading.Thread):
    """A worker for a single conversation. A new one is created every time the /start command is sent."""

    def __init__(self, bot: telegram.Bot, chat: telegram.Chat, *args, **kwargs):
        # Initialize the thread
        super().__init__(name=f"ChatThread {chat.first_name}", *args, **kwargs)
        # Store the bot and chat info inside the class
        self.bot = bot
        self.chat = chat
        # Open a new database session
        self.session = db.Session()
        # Get the user db data from the users and admin tables
        self.user = self.session.query(db.User).filter(db.User.user_id == self.chat.id).one_or_none()
        self.admin = self.session.query(db.Admin).filter(db.Admin.user_id == self.chat.id).one_or_none()
        # The sending pipe is stored in the ChatWorker class, allowing the forwarding of messages to the chat process
        self.queue = queuem.Queue()

    def run(self):
        """The conversation code."""
        # TODO: catch all the possible exceptions
        # Welcome the user to the bot
        self.bot.send_message(self.chat.id, strings.conversation_after_start)
        # If the user isn't registered, create a new record and add it to the db
        if self.user is None:
            # Create the new record
            self.user = db.User(self.chat)
            # Add the new record to the db
            self.session.add(self.user)
            # Commit the transaction
            self.session.commit()
        # If the user is not an admin, send him to the user menu
        if self.admin is None:
            self.__user_menu()
        # If the user is an admin, send him to the admin menu
        else:
            self.__admin_menu()

    def stop(self, reason: str=""):
        """Gracefully stop the worker process"""
        # Send a stop message to the thread
        self.queue.put(StopSignal(reason))
        # Wait for the thread to stop
        self.join()

    def __receive_next_update(self) -> telegram.Update:
        """Get the next update from the queue.
        If no update is found, block the process until one is received.
        If a stop signal is sent, try to gracefully stop the thread."""
        # Pop data from the queue
        try:
            data = self.queue.get(timeout=int(configloader.config["Telegram"]["conversation_timeout"]))
        except queuem.Empty:
            # If the conversation times out, gracefully stop the thread
            self.__graceful_stop()
        # Check if the data is a stop signal instance
        if isinstance(data, StopSignal):
            # Gracefully stop the process
            self.__graceful_stop()
        # Return the received update
        return data

    def __wait_for_specific_message(self, items:typing.List[str]) -> str:
        """Continue getting updates until until one of the strings contained in the list is received as a message."""
        while True:
            # Get the next update
            update = self.__receive_next_update()
            # Ensure the update contains a message
            if update.message is None:
                continue
            # Ensure the message contains text
            if update.message.text is None:
                continue
            # Check if the message is contained in the list
            if update.message.text not in items:
                continue
            # Return the message text
            return update.message.text

    def __user_menu(self):
        """Function called from the run method when the user is not an administrator.
        Normal bot actions should be placed here."""
        # Create a keyboard with the user main menu
        keyboard = [[telegram.KeyboardButton(strings.menu_order)],
                    [telegram.KeyboardButton(strings.menu_order_status)],
                    [telegram.KeyboardButton(strings.menu_add_credit)],
                    [telegram.KeyboardButton(strings.menu_info)]]
        # Send the previously created keyboard to the user (ensuring it can be clicked only 1 time)
        self.bot.send_message(self.chat.id, strings.conversation_open_user_menu.format(username=str(self.user)),
                              reply_markup=telegram.ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        # Wait for a reply from the user
        # TODO: change this
        selection = self.__wait_for_specific_message([strings.menu_order, strings.menu_order_status,
                                                      strings.menu_add_credit, strings.menu_info])
        # If the user has selected the Order option...
        if selection == strings.menu_order:
            ...
        # If the user has selected the Order Status option...
        elif selection == strings.menu_order_status:
            ...
        # If the user has selected the Add Credit option...
        elif selection == strings.menu_add_credit:
            ...
        # If the user has selected the Bot Info option...
        elif selection == strings.menu_info:
            ...


    def __admin_menu(self):
        """Function called from the run method when the user is an administrator.
        Administrative bot actions should be placed here."""
        self.bot.send_message(self.chat.id, "Sei un Amministralol")

    def __graceful_stop(self):
        """Handle the graceful stop of the thread."""
        # Notify the user that the session has expired
        self.bot.send_message(self.chat.id, strings.conversation_expired)
        # Close the database session
        # End the process
        sys.exit(0)
