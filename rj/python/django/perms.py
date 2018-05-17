# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import magic
from backend.apps.document.models import Document
from backend.apps.auth.models import SecureToken
from backend.apps.document import models, serializers
from backend.apps.mixins.filters import CamelCaseOrderingFilter
from django.contrib.auth import get_user_model
from django.http import HttpResponse, Http404
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets, pagination, filters, generics, response

User = get_user_model()


class DocumentDownloadView(SingleObjectMixin, View):
    permission_required = 'document.view_document'
    queryset = models.Document.objects.all()

    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')
        try:
            token = SecureToken.objects.active().get(token=token, category=SecureToken.DOWNLOAD)
        except SecureToken.DoesNotExist:
            raise Http404

        user = token.user
        document = token.content_object

        if not document.file:
            raise Http404

        document.log_download(user)
        content_type = magic.from_file(document.file.file.name, mime=True)
        response = HttpResponse(document.file, content_type=content_type)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(document.filename)
        return response


class DocumentDownloadRetrieveView(generics.RetrieveAPIView):
    serializer_class = serializers.DocumentMetaSerializer
    queryset = models.Document.objects.all()
    filter_backends = (CamelCaseOrderingFilter, filters.SearchFilter,)
    pagination_class = pagination.LimitOffsetPagination
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')

        try:
            token = SecureToken.objects.get(token=token, category=SecureToken.DOWNLOAD)
            request.user = token.user
        except SecureToken.DoesNotExist:
            return response.Response('invalid token')

        return super(DocumentDownloadRetrieveView, self).get(request, *args, **kwargs)


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.DocumentSerializer
    queryset = models.Document.objects.all()
    filter_backends = (CamelCaseOrderingFilter, filters.SearchFilter, filters.DjangoFilterBackend,)
    pagination_class = pagination.LimitOffsetPagination
    model = 'document'
    filter_fields = ['sticky']

    def get_queryset(self):
        qs = get_objects_for_user(self.request.user, 'view_{}'.format(self.model), klass=models.Document.objects.all())
        return qs

    def filter_queryset(self, queryset):
        view_access = self.request.query_params.get('viewAccess', 0)
        user = User.objects.get(id=view_access) if User.objects.filter(id=view_access).exists() else None
        if user and user == self.request.user:
            queryset = queryset.exclude(owner=user)
        elif user:
            queryset = get_objects_for_user(user, 'view_{}'.format(self.model), klass=queryset)

        if 'owner' in self.request.query_params:
            queryset = queryset.filter(owner=self.request.user)

        return super(DocumentViewSet, self).filter_queryset(queryset)

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.log_create(self.request.user)
        instance.set_owner_perms(self.model)

    def perform_destroy(self, instance):
        instance.log_delete(self.request.user)
        super(DocumentViewSet, self).perform_destroy(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.log_modify(self.request.user)


class PromotionViewSet(DocumentViewSet):
    serializer_class = serializers.PromotionSerializer
    queryset = models.Promotion.objects.all()
    model = 'promotion'

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_promotion', klass=models.Promotion.objects.all())


class PostViewSet(DocumentViewSet):
    serializer_class = serializers.PostSerializer
    queryset = models.Post.objects.all()
    model = 'post'

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_post', klass=models.Post.objects.all())


class PriceListViewSet(DocumentViewSet):
    serializer_class = serializers.PriceListSerializer
    queryset = models.PriceList.objects.all()
    model = 'price'

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_pricelist', klass=models.PriceList.objects.all())
