# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from backend.apps.contact.models import Contact
from backend.apps.auth.models import SecureToken, User
from backend.apps.document import managers
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import assign_perm, get_users_with_perms



@python_2_unicode_compatible
class File(models.Model):
    PRICE_LIST = 'pricelist'
    PROMOTION = 'promotion'
    DOCUMENT = 'document'
    POST = 'post'

    CATEGORY_CHOICES = (
        (PRICE_LIST, _('Price-list')),
        (PROMOTION, _('Promotion')),
        (POST, _('Post')),
        (DOCUMENT, _('Document')),
    )

    POST_CHANGED = 'post_changed'
    POST_REMINDER = 'post_reminder'
    POST_NEW = 'post_new'
    DOCUMENT_REMINDER = 'document_reminder'
    DOCUMENT_CHANGED = 'document_changed'
    DOCUMENT_NEW = 'document_new'

    name = models.CharField(max_length=255)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    file = models.FileField(blank=True)
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    is_delete = models.BooleanField(default=False)
    notify = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    sticky = models.BooleanField(default=False)
    contacts_to_notify = models.ManyToManyField(Contact, blank=True, null=True)

    objects = managers.FileManager()
    deleted_objects = managers.DeletedFileManager()
    all_objects = managers.AllFileManager()

    class Meta:
        permissions = (
            ('view_file', _('Can view file')),
        )

    def __str__(self):
        return self.name

    @property
    def view_access(self):
        perm = 'view_{}'.format(self.category)
        return [user for user, perms in get_users_with_perms(self, attach_perms=True).iteritems()
                if perm in perms and user != self.owner]

    @property
    def created_at(self):
        log = self.logs.get(type=FileLog.CREATE)
        return log.datetime

    @property
    def modified_at(self):
        modify_logs = self.logs.filter(type=FileLog.MODIFY)
        if modify_logs.exists():
            return modify_logs.latest('datetime').datetime
        else:
            return self.created_at

    @property
    def filename(self):
        return self.file.name

    @property
    def size(self):
        return self.file.size if self.file else 0

    def delete(self, using=None, keep_parents=False):
        delete_log = self.logs.filter(type=FileLog.DELETE)
        if not delete_log.exists():
            self.log_delete()
        self.is_delete = True
        self.save()

    def log_create_or_modify(self, user=None):
        create_log = self.logs.filter(type=FileLog.CREATE)
        type = FileLog.MODIFY if create_log.exists() else FileLog.CREATE

        self.__log(user, type)

    def log_create(self, user=None):
        self.__log(user, type=FileLog.CREATE)

    def log_modify(self, user=None):
        self.__log(user, type=FileLog.MODIFY)

    def log_download(self, user=None):
        self.__log(user, type=FileLog.DOWNLOAD)

    def log_notify(self, user=None):
        self.__log(user, type=FileLog.NOTIFY)

    def log_delete(self, user=None):
        self.__log(user, type=FileLog.DELETE)

    def set_owner_perms(self, model=None):
        assign_perm('document.view_file', self.owner, self)
        assign_perm('document.delete_file', self.owner, self)
        assign_perm('document.change_file', self.owner, self)
        if model:
            assign_perm('document.view_{}'.format(model), self.owner, self)
            assign_perm('document.delete_{}'.format(model), self.owner, self)
            assign_perm('document.change_{}'.format(model), self.owner, self)

    def frontend_download_url(self, user):
        token, created = SecureToken.objects.active().get_or_create(
            user=user,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
            category=SecureToken.DOWNLOAD
        )
        return 'http://{domain}/#/download/{id}/{token}'.format(
                    domain=Site.objects.first().domain,
                    id=self.pk,
                    token=token.token,
                )

    def notify_contacts(self, notify_type='document_reminder'):
        html_template, subject, text_template = self._prepare_notificaiton(notify_type)

        if any([
            not self.notify,
            notify_type == 'document_issued_reminder' and not self.is_important
        ]):
            return

        for contact in self.contacts_to_notify.all():
            context = {
                'document': self,
                'recipient': contact,
                'document_download_url': self.frontend_download_url(contact.owner),
            }
            message = render_to_string(text_template, context=context)
            html_message = render_to_string(html_template, context=context)
            contact.email_user(subject, message, html_message=html_message)

    def notify_receiver(self, notify_type='document_reminder', notify_count=5):
        html_template, subject, text_template = self._prepare_notificaiton(notify_type)

        if any([
            not self.notify,
            notify_type == 'document_issued_reminder' and not self.is_important
        ]):
            return

        users_to_notify = {}
        for user, perms in get_users_with_perms(self, attach_perms=True).iteritems():
            if all([
                'view_document' in perms,
                not user.is_superuser,
                user != self.owner,
                not self.logs.filter(file=self, user=user, type=FileLog.DOWNLOAD).exists(),
                notify_type != 'document_reminder' or self.logs.filter(user=user, type=FileLog.NOTIFY).count() <= notify_count
            ]):
                users_to_notify[user] = {
                    'document': self,
                    'recipient': user,
                    'document_download_url': self.frontend_download_url(user),
                }

        for user, context in users_to_notify.items():
            message = render_to_string(text_template, context=context)
            html_message = render_to_string(html_template, context=context)
            user.email_user(subject, message, html_message=html_message)
            self.log_notify(user)


    def notify_users(self, notify_type='document_reminder'):
        html_template, subject, text_template = self._prepare_notificaiton(notify_type)

        if any([
            not self.notify,
            notify_type == 'document_issued_reminder' and not self.is_important
        ]):
            return

        users_to_notify = {}
        for user, perms in get_users_with_perms(self, attach_perms=True).iteritems():
            if all([
                'view_document' in perms,
                not user.is_superuser,
                user != self.owner,
                not self.logs.filter(file=self, user=user, type=FileLog.DOWNLOAD).exists()
            ]):
                users_to_notify[user] = {
                    'document': self,
                    'recipient': user,
                    'document_download_url': self.frontend_download_url(user),
                }
                users_to_notify.update({contact: {
                    'document': self,
                    'recipient': contact,
                    'document_download_url': self.frontend_download_url(contact.owner),
                    } for contact in user.contact_set.all()
                })
                self.log_notify(user)
        for user, context in users_to_notify.items():
            message = render_to_string(text_template, context=context)
            html_message = render_to_string(html_template, context=context)
            user.email_user(subject, message, html_message=html_message)

    def notify_members(self, notify_type='post_reminder'):
        html_template, subject, text_template = self._prepare_notificaiton(notify_type)

        if any([
            not self.notify,
            notify_type == 'post_issued_reminder' and not self.is_important
        ]):
            return

        users_to_notify = {}
        members = User.objects.filter(groups__name='Members')
        for member in members:
            if all([
                not member.is_superuser,
                member != self.owner,
                not self.logs.filter(file=self, user=member, type=FileLog.DOWNLOAD).exists()
            ]):
                users_to_notify[member] = {
                    'document': self,
                    'recipient': member,
                    'document_download_url': self.frontend_download_url(member),
                }
                self.log_notify(member)

        for user, context in users_to_notify.items():
            message = render_to_string(text_template, context=context)
            html_message = render_to_string(html_template, context=context)
            user.email_user(subject, message, html_message=html_message)

    def notify_owner(self, notify_count=5):
        """Notify owner that users with view permission doesn't download document after 5 notifications"""
        if not self.notify:
            return
        users = [user for user, perms in get_users_with_perms(self, attach_perms=True).iteritems()
                 if all([
                    'view_document' in perms,
                    not user.is_superuser,
                    user != self.owner,
                    self.logs.filter(user=user, type=FileLog.NOTIFY).count() <= notify_count,
                    not self.logs.filter(file=self, user=user, type=FileLog.DOWNLOAD).exists()
                    ])]

        if not users:
            return
        context = {
            'recipient': self.owner,
            'users': users,
            'document': self,
        }
        subject = '[ACWL] Document not downloaded'
        message = render_to_string('email/notifications/document_not_downloaded.txt', context=context)
        html_message = render_to_string('email/notifications/document_not_downloaded.html', context=context)
        self.log_notify(self.owner)
        self.owner.email_user(subject, message, html_message=html_message)

    def __log(self, user=None, type=None):
        log = FileLog(user=user, type=type, file=File.objects.get(id=self.id))
        log.save()

    def _prepare_notificaiton(self, notify_type):
        if notify_type == File.DOCUMENT_REMINDER:
            subject = '[ACWL] Document issued reminder'
            text_template = 'email/notifications/document_reminder.txt'
            html_template = 'email/notifications/document_reminder.html'
        elif notify_type == File.DOCUMENT_NEW:
            subject = '[ACWL] Document issued'
            text_template = 'email/notifications/document_new.txt'
            html_template = 'email/notifications/document_new.html'
        elif notify_type == File.DOCUMENT_CHANGED:
            subject = '[ACWL] Document changed'
            text_template = 'email/notifications/document_changed.txt'
            html_template = 'email/notifications/document_changed.html'
        elif notify_type == File.POST_REMINDER:
            subject = '[ACWL] Post issued reminder'
            text_template = 'email/notifications/document_reminder.txt'
            html_template = 'email/notifications/document_reminder.html'
        elif notify_type == File.POST_NEW:
            subject = '[ACWL] Post issued'
            text_template = 'email/notifications/document_new.txt'
            html_template = 'email/notifications/document_new.html'
        elif notify_type == File.POST_CHANGED:
            subject = '[ACWL] Post changed'
            text_template = 'email/notifications/document_changed.txt'
            html_template = 'email/notifications/document_changed.html'
        else:
            raise ValueError('Type not supported')
        return html_template, subject, text_template


@python_2_unicode_compatible
class FileLog(models.Model):
    CREATE = 'create'
    MODIFY = 'modify'
    DOWNLOAD = 'download'
    DELETE = 'delete'
    NOTIFY = 'notify'

    TYPES_CHOICES = (
        (CREATE, _('Create')),
        (MODIFY, _('Modify')),
        (DOWNLOAD, _('Download')),
        (DELETE, _('Delete')),
        (NOTIFY, _('Notify')),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    datetime = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=255, choices=TYPES_CHOICES)
    file = models.ForeignKey(File, related_name='logs')

    class Meta:
        verbose_name = _('File Log')
        verbose_name_plural = _('File Logs')

    def __str__(self):
        return ' '.join(('log:', str(self.file), self.type))

    def notify_file_owner(self):
        context = {
            'document_log': self,
        }
        subject = '[ACWL] Document downloaded'
        message = render_to_string('email/notifications/document_downloaded.txt', context=context)
        html_message = render_to_string('email/notifications/document_downloaded.html', context=context)
        self.file.owner.email_user(subject, message, html_message=html_message)


class Promotion(File):
    deleted_objects = managers.DeletedFileManager()
    all_objects = managers.AllPromotionManager()

    def __init__(self, *args, **kwargs):
        self._meta.get_field('category').default = self.PROMOTION
        super(Promotion, self).__init__(*args, **kwargs)

    objects = managers.PromotionManager()

    class Meta:
        proxy = True
        permissions = (
            ('view_promotion', _('Can view promotion')),
        )

    def set_owner_perms(self, model='promotion'):
        super(Promotion, self).set_owner_perms(model=model)


class Post(File):
    deleted_objects = managers.DeletedFileManager()
    all_objects = managers.AllPostManager()

    def __init__(self, *args, **kwargs):
        self._meta.get_field('category').default = self.POST
        super(Post, self).__init__(*args, **kwargs)

    objects = managers.PostManager()

    class Meta:
        proxy = True
        permissions = (
            ('view_post', _('Can view post')),
        )

    def set_owner_perms(self, model='post'):
        super(Post, self).set_owner_perms(model=model)


class PriceList(File):
    deleted_objects = managers.DeletedFileManager()
    all_objects = managers.AllPriceListManager()

    def __init__(self, *args, **kwargs):
        self._meta.get_field('category').default = self.PRICE_LIST
        super(PriceList, self).__init__(*args, **kwargs)

    objects = managers.PriceListManager()

    class Meta:
        proxy = True
        permissions = (
            ('view_pricelist', _('Can view price-list')),
        )

    def set_owner_perms(self, model='pricelist'):
        super(PriceList, self).set_owner_perms(model=model)


class Document(File):
    deleted_objects = managers.DeletedFileManager()
    all_objects = managers.AllDocumentManager()

    def __init__(self, *args, **kwargs):
        self._meta.get_field('category').default = self.DOCUMENT
        super(Document, self).__init__(*args, **kwargs)

    objects = managers.DocumentManager()

    class Meta:
        proxy = True
        permissions = (
            ('view_document', _('Can view document')),
        )

    def set_owner_perms(self, model='document'):
        super(Document, self).set_owner_perms(model=model)

