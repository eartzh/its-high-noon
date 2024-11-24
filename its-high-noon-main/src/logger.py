import logging

# Define TRACE level number - should be less than DEBUG (10)
TRACE_LEVEL_NUM = 5
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


# Create a custom logger class to add the trace method
class CustomLogger(logging.Logger):
    def trace(self, message, *args, **kwargs):
        """
        Log a message with TRACE level.

        Args:
            message: The message to log
            args: Arguments to merge into msg using string formatting
            kwargs: Keyword arguments to pass to underlying logger
        """
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            self._log(TRACE_LEVEL_NUM, message, args, **kwargs)


# Set the custom logger class as the default
logging.setLoggerClass(CustomLogger)


# Example usage
def setup_logger(log_file='app.log'):
    """
    Set up a logger with both console and file handlers.

    Args:
        log_file: Path to the log file

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger()
    logger.setLevel(TRACE_LEVEL_NUM)

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
