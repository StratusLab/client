
MSG_CLIENTS = {'amazonsqs' : 'AmazonSqsQueue',
               'rest'      : 'RestPublisher',
               'dirq'      : 'DirectoryQueue',
               'email'     : 'EmailClient',
               'stomp'     : 'StompClient',
               'amqp'      : 'AmqpClient'}

MSG_TYPES = sorted(MSG_CLIENTS.keys())
