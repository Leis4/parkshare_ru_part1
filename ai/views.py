from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class RecommendationsAPIView(APIView):
    """
    Возвращает заглушку AI-рекомендаций.
    """
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "recommendations": [],
                "message": "AI-рекомендации пока не реализованы",
            },
            status=status.HTTP_200_OK,
        )


class StressIndexAPIView(APIView):
    """
    Заглушка индекса загруженности парковок.
    """
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "stress_index": 0,
                "details": "AI-индекс загруженности пока не реализован",
            },
            status=status.HTTP_200_OK,
        )


class DepartureAssistantAPIView(APIView):
    """
    Заглушка помощника по времени выезда.
    Например, в будущем тут можно будет учитывать пробки, время до парковки и т.п.
    """

    def post(self, request, *args, **kwargs):
        # На будущее: можно принимать в body:
        # - пункт назначения
        # - желаемое время прибытия
        # - примерное время на парковку/поиск места
        return Response(
            {
                "suggested_departure_time": None,
                "message": "AI-помощник по выезду пока не реализован",
            },
            status=status.HTTP_200_OK,
        )
