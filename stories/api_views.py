class MultiStoriesSerializerViewSetMixin:
    serializer_action_classes = {}

    def get_serializer_class(self):
        serializer = self.serializer_action_classes.get(self.action)
        if not serializer:
            serializer = super().get_serializer_class()
        return serializer
