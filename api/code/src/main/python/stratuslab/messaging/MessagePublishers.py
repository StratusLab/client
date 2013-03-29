import base64
import json

from stratuslab.messaging.MsgClientFactory import getMsgClient
from stratuslab.Exceptions import InputException
from stratuslab.image.Image import Image

class SingleMessagePublisher(object):

    def __init__(self, message, configHolder):
        if not isinstance(message, basestring):
            raise InputException("Message should be 'str' or 'unicode'.")
        self.message = message
        self.client = getMsgClient(configHolder)

    def publish(self):
        self.client.deliver(self.message)

class ImageIdPublisher(SingleMessagePublisher):
    """Publishes base64 encoded JSON message with Marketplace image ID as 
    an entry in a map with a key 'imageid'.
    """

    IMAGEID_KEY = 'imageid'

    def __init__(self, message, image_id, configHolder):
        """message - empty string or JSON representation of a map 
        (can be base64 encoded).
        image_id - Marketplace image ID
        """
        super(ImageIdPublisher, self).__init__(message, configHolder)
        if not Image.isImageId(image_id):
            raise InputException('Marketplace image ID is expected.')
        self.message = self._set_imageid_on_message(self.message, image_id)

    def _set_imageid_on_message(self, message, imageid):
        'message - empty string or JSON and can be base64 encoded'
        if len(message) == 0:
            message = '{}'
        if not message.startswith('{'):
            # Assume this is base64 encoded message.
            message = base64.b64decode(message)
        try:
            message_dict = json.loads(message)
        except Exception, ex:
            raise ValueError("Couldn't load JSON message: %s" %  str(ex))
        message_dict[ImageIdPublisher.IMAGEID_KEY] = imageid
        return json.dumps(message_dict)
