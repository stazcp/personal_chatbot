class CustomAPIError(Exception):
    def __init__(self, message, error_type, status_code):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code

    def to_dict(self):
        return {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "status_code": self.status_code
            }
        }