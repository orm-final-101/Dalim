from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.exceptions import MethodNotAllowed, NotFound
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from dj_rest_auth.registration.views import RegisterView
from .models import CustomUser, Record, JoinedCrew, JoinedRace
from crews.models import CrewReview
from crews.serializers import CrewListSerializer, ProfileCrewReviewSerializer
from races.models import Race, RaceReview
from races.serializers import RaceListSerializer, ProfileRaceReviewSerializer
from boards.models import Post, Comment, Like
from boards.serializers import (
    PostListSerializer,
    ProfileCommentSerializer,
    ProfileLikedPostSerializer,
)
from .serializers import (
    CustomRegisterSerializer,
    ProfileSerializer,
    RecordSerialiser,
    JoinedCrewSerializer,
    JoinedRaceGetSerializer,
    JoinedRacePostSerializer,
    OpenProfileSerializer,
)


class CustomRegisterView(RegisterView):
    serializer_class = CustomRegisterSerializer


# mypage/info/ : 유저 정보 CRUD
class UserInfoViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        try:
            return CustomUser.objects.get(pk=self.request.user.pk)
        except CustomUser.DoesNotExist:
            raise NotFound("User not found")

    @extend_schema(request=ProfileSerializer)
    def list(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = ProfileSerializer(user)
        return Response(serializer.data)

    @extend_schema(request=ProfileSerializer)
    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = ProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# mypage/record/ : 달림 기록 CRUD
@extend_schema(methods=["POST", "PATCH"], request=RecordSerialiser)
class RecordViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        queryset = Record.objects.filter(user=request.user)
        serializer = RecordSerialiser(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = RecordSerialiser(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def partial_update(self, request, pk=None):
        try:
            record = Record.objects.get(pk=pk, user=request.user)
        except Record.DoesNotExist:
            return Response({"error": "Record not found"}, status=404)

        serializer = RecordSerialiser(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def destroy(self, request, pk=None):
        try:
            record = Record.objects.get(pk=pk, user=request.user)
        except Record.DoesNotExist:
            return Response({"error": "Record not found"}, status=404)

        record.delete()
        serializers = RecordSerialiser()
        serializers.update_user_level(request.user)
        return Response(status=204)


# /mypage/crew/ : 내가 가입한 크루 목록
class MypageCrewViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return CustomUser.objects.get(pk=self.request.user.pk)
        except CustomUser.DoesNotExist:
            raise NotFound("User not found")

    def list(self, request, *args, **kwargs):
        user = self.get_object()
        joined_crews = JoinedCrew.objects.filter(user=user)
        serializer = JoinedCrewSerializer(
            joined_crews, many=True, context={"request": request}
        )
        return Response(serializer.data)


# /mypage/race/ : 내가 신청한 대회 내역
# /mypage/race/<int:joined_race_id> : 내 대회 기록
@extend_schema(methods=["GET", "POST", "PATCH", "DELETE"])
class RaceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        queryset = JoinedRace.objects.filter(user=request.user)
        serializer = JoinedRaceGetSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        request=inline_serializer(
            name="RaceCreateInlineSerializer",
            fields={"race_id": serializers.IntegerField()},
        )
    )
    def create(self, request):
        race_id = request.data.get("race_id")

        try:
            race = Race.objects.get(pk=race_id)
        except:
            # 해당하는 race 없을 시 에러메세지 반환
            return Response({"error": "해당 대회가 존재하지 않습니다."}, status=404)

        # request.user.pk와 race.id를 이용해 JoinedRace 객체를 생성
        data = {"user": request.user.pk, "race": race.id}

        # 이미 user와 race가 같은 객체가 있는지 확인
        if JoinedRace.objects.filter(user=data["user"], race=data["race"]).exists():
            return Response({"error": "이미 참가한 대회입니다."}, status=400)

        serializer = JoinedRacePostSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @extend_schema(
        request=inline_serializer(
            name="RaceUpdateInlineSerializer",
            fields={"race_record": serializers.CharField()},
        )
    )
    def partial_update(self, request, pk):
        race_record = request.data.get("race_record")

        try:
            joined_race = JoinedRace.objects.get(pk=pk, user=request.user)
        except JoinedRace.DoesNotExist:
            return Response(
                {"error": "해당 JoinedRace가 존재하지 않습니다."}, status=404
            )

        serializer = JoinedRacePostSerializer(
            joined_race, data={"race_record": race_record}, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def destroy(self, request, pk):
        try:
            joined_race = JoinedRace.objects.get(pk=pk, user=request.user)
        except JoinedRace.DoesNotExist:
            return Response(
                {"error": "해당 JoinedRace가 존재하지 않습니다."}, status=404
            )

        joined_race.delete()
        return Response(status=204)


# /mypage/favorites/ : 내가 찜한 크루, 대회 목록
class MypageFavoritesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return CustomUser.objects.get(pk=self.request.user.pk)
        except CustomUser.DoesNotExist:
            raise NotFound("사용자를 찾을 수 없습니다.")

    def list(self, request, *args, **kwargs):
        user = self.get_object()
        favorite_crews = [favorite.crew for favorite in user.favorite_crews.all()]
        favorite_races = [favorite.race for favorite in user.favorite_races.all()]

        crew_serializer = CrewListSerializer(
            favorite_crews, many=True, context={"request": request}
        )
        race_serializer = RaceListSerializer(
            favorite_races, many=True, context={"request": request}
        )

        response_data = {"crew": crew_serializer.data, "race": race_serializer.data}

        return Response(response_data)


# /<int:pk>/profile/ : 유저 오픈프로필 조회
class ProfileViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        user_serializer = OpenProfileSerializer(user)
        post_serializer = PostListSerializer(
            Post.objects.filter(author=user), many=True
        )
        comments_serializer = ProfileCommentSerializer(
            Comment.objects.filter(author=user), many=True
        )
        crew_review_serializer = ProfileCrewReviewSerializer(
            CrewReview.objects.filter(author=user), many=True
        )
        race_review_serializer = ProfileRaceReviewSerializer(
            RaceReview.objects.filter(author=user), many=True
        )

        fin_data = {
            "user": user_serializer.data,
            "posts": post_serializer.data,
            "comments": comments_serializer.data,
            "reviews": {
                "crew": crew_review_serializer.data,
                "race": race_review_serializer.data,
            },
        }

        # request.user와 pk가 일치하는 경우에만 'likes' 항목을 추가
        if request.user.pk == user.pk:
            liked_post_serializer = ProfileLikedPostSerializer(
                Like.objects.filter(author=user), many=True
            )
            fin_data["likes"] = liked_post_serializer.data

        return Response(fin_data)
