from django.shortcuts import get_object_or_404
from django import forms
from django.forms import Form, ModelForm, ModelChoiceField, ChoiceField
from django.contrib.auth.models import User, Group
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _, string_concat
from django.db.models.fields import BLANK_CHOICE_DASH
from django.core.validators import RegexValidator
from multiupload.fields import MultiFileField
from api import models

class DateInput(forms.DateInput):
    input_type = 'date'

class CreateUserForm(ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ('username', 'email', 'password')

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email')

class AddLinkForm(ModelForm):
    class Meta:
        model = models.UserLink
        fields = ('type', 'value', 'relevance')

class ChangePasswordForm(Form):
    old_password = forms.CharField(widget=forms.PasswordInput(), label=_('Old Password'))
    new_password = forms.CharField(widget=forms.PasswordInput(), label=_('New Password'))
    new_password2 = forms.CharField(widget=forms.PasswordInput(), label=_('New Password Again'))

    def clean(self):
        if ('new_password' in self.cleaned_data and 'new_password2' in self.cleaned_data
            and self.cleaned_data['new_password'] == self.cleaned_data['new_password2']):
            return self.cleaned_data
        raise forms.ValidationError(_("The two password fields did not match."))

def getGirls():
    girls = models.Card.objects.values('idol__name').annotate(total=Count('idol__name')).order_by('-total', 'idol__name')
    return [('', '')] + [(girl['idol__name'], girl['idol__name']) for girl in girls]

class UserPreferencesForm(ModelForm):
    best_girl = ChoiceField(label=_('Best Girl'), choices=getGirls(), required=False)
    def __init__(self, *args, **kwargs):
        super(UserPreferencesForm, self).__init__(*args, **kwargs)
        self.fields['birthdate'].widget = DateInput()
        self.fields['birthdate'].widget.attrs.update({
            'class': 'calendar-widget',
            'data-role': 'data',
        })

    class Meta:
        model = models.UserPreferences
        fields = ('color', 'best_girl', 'location', 'birthdate', 'private', 'description', 'private')

class AccountForm(ModelForm):
    class Meta:
        model = models.Account
        fields = ('nickname', 'language', 'os', 'friend_id', 'rank')

class OwnedCardModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return unicode(obj.card) + ' ' + ('idolized' if obj.idolized else '')

class FullAccountForm(ModelForm):
    center = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.filter(pk=0), required=False, label=_('Center'))
    # Always override this queryset to set the current account only
    # form.fields['center'].queryset = models.OwnedCard.objects.filter(owner_account=owned_account, stored='Deck')
    class Meta:
        model = models.Account
        fields = ('nickname', 'center', 'rank', 'friend_id', 'language', 'os', 'device', 'play_with', 'accept_friend_requests')

class FullAccountNoFriendIDForm(FullAccountForm):
    class Meta:
        model = models.Account
        fields = ('nickname', 'center', 'rank', 'os', 'device', 'play_with', 'accept_friend_requests')

class SimplePasswordForm(Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'off'}), label=_('Password'))

class ConfirmDelete(forms.Form):
    confirm = forms.BooleanField(required=True, initial=False, label=_('Confirm that you want to delete it.'))
    thing_to_delete = forms.IntegerField(widget=forms.HiddenInput, required=True)

class TransferCodeForm(ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), label=_('Password'))
    confirm = forms.BooleanField(required=True, initial=False, label=_('Delete previously saved transfer code'))
    class Meta:
        model = models.Account
        fields = ('transfer_code',)

class _OwnedCardForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(_OwnedCardForm, self).__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'card'):
            if self.instance.card.is_special or self.instance.card.is_promo:
                self.fields['idolized'].widget = forms.HiddenInput()

    def save(self, commit=True):
        instance = super(_OwnedCardForm, self).save(commit=False)
        if instance.card.is_special:
            instance.idolized = False
        if instance.card.is_promo:
            instance.idolized = True
        if commit:
            instance.save()
        return instance

class QuickOwnedCardForm(_OwnedCardForm):
    card = forms.IntegerField()
    class Meta:
        model = models.OwnedCard
        fields = ('card', 'owner_account', 'idolized')

class EditQuickOwnedCardForm(_OwnedCardForm):
    card = forms.IntegerField()
    class Meta:
        model = models.OwnedCard
        fields = ('idolized',)

class StaffAddCardForm(ModelForm):
    card = forms.IntegerField()
    owner_account = forms.IntegerField()

    def save(self, commit=True):
        self.instance.card = get_object_or_404(models.Card, pk=self.cleaned_data['card'])
        self.instance.owner_account = get_object_or_404(models.Account, pk=self.cleaned_data['owner_account'])
        return super(StaffAddCardForm, self).save(commit)

    class Meta:
        model = models.OwnedCard
        fields = ('card', 'owner_account', 'stored', 'idolized', 'max_level', 'max_bond', 'skill')
        exclude = ('card', 'owner_account')

class OwnedCardForm(_OwnedCardForm):
    class Meta:
        model = models.OwnedCard
        fields = ('owner_account', 'stored', 'idolized', 'max_level', 'max_bond', 'skill')

class EditOwnedCardForm(_OwnedCardForm):
    class Meta:
        model = models.OwnedCard
        fields = ('stored', 'idolized', 'max_level', 'max_bond', 'skill')

def getOwnedCardForm(form, accounts, owned_card=None):
    form.fields['owner_account'].queryset = accounts
    form.fields['owner_account'].required = True
    form.fields['owner_account'].empty_label = None
    if owned_card is not None:
        if not owned_card.card.skill:
            form.fields.pop('skill')
    return form

class EventParticipationForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('account', 'ranking', 'points', 'song_ranking')

class EventParticipationNoSongForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('account', 'ranking', 'points')

class EventParticipationNoAccountForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('ranking', 'points', 'song_ranking')

class EventParticipationNoSongNoAccountForm(ModelForm):
    class Meta:
        model = models.EventParticipation
        fields = ('ranking', 'points')

def getEventParticipationForm(form, accounts):
    form.fields['account'].queryset = accounts
    form.fields['account'].required = True
    form.fields['account'].empty_label = None
    return form

class UserProfileStaffForm(ModelForm):
    class Meta:
        model = models.UserPreferences
        fields = ('status', 'donation_link', 'donation_link_title', 'description', 'location', 'location_changed')

class AccountStaffForm(ModelForm):
    owner_id = forms.IntegerField(required=False)
    center = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=True)
    class Meta:
        model = models.Account
        fields = ('owner_id', 'friend_id', 'verified', 'rank', 'os', 'device', 'center')

class MultiImageField(MultiFileField, forms.ImageField):
    pass

imgur_regexp = '^https?:\/\/(\w+\.)?imgur.com\/(?P<imgur>[\w\d]+)(\.[a-zA-Z]{3})?$'

class _Activity(ModelForm):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        initial['right_picture'] = ''
        kwargs['initial'] = initial
        super(_Activity, self).__init__(*args, **kwargs)
        self.fields['right_picture'].help_text = _('Use a valid imgur URL such as http://i.imgur.com/6oHYT4B.png')
        self.fields['right_picture'].label = _('Picture')
        self.fields['right_picture'].validators.append(RegexValidator(
            regex=imgur_regexp,
            message='Invalid Imgur URL',
            code='invalid_url',
        ))

class EditActivityPicture(_Activity):
    def __init__(self, *args, **kwargs):
        super(EditActivityPicture, self).__init__(*args, **kwargs)
        self.fields['right_picture'].required = True

    class Meta:
        model = models.Activity
        fields = ('right_picture',)

class CustomActivity(_Activity):
    account_id = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(CustomActivity, self).__init__(*args, **kwargs)
        self.fields['account_id'].widget = forms.HiddenInput()
        self.fields['message_data'].widget = forms.Textarea()
        self.fields['message_data'].required = True
        self.fields['message_data'].label = _('Message')
        self.fields['message_data'].widget.attrs.update({'maxlength': 1200})
        self.fields['message_data'].help_text = _('Write whatever you want. You can add formatting and links using Markdown.')

    class Meta:
        model = models.Activity
        fields = ('account_id', 'message_data', 'right_picture')

class VerificationRequestForm(ModelForm):
    upload_images = MultiImageField(min_num=0, max_num=10, required=False, help_text=_('If your files are too large, send them one by one. First upload one image, then edit your request with the second one, and so on. If even one image doesn\'t work, please resize your images.'))

    def __init__(self, *args, **kwargs):
        account = None
        if 'account' in kwargs:
            account = kwargs.pop('account')
        super(VerificationRequestForm, self).__init__(*args, **kwargs)
        if account is not None:
            if account.language != 'JP' and account.language != 'EN':
                self.fields['verification'].choices = ((0, ''), (1, _('Silver Verified')))
            elif account.rank < 195:
                self.fields['verification'].choices = ((0, ''), (1, _('Silver Verified')), (2, _('Gold Verified')))

    class Meta:
        model = models.VerificationRequest
        fields = ('verification', 'comment', 'upload_images', 'allow_during_events')

class StaffVerificationRequestForm(ModelForm):
    images = MultiImageField(min_num=0, max_num=10, required=False)
    status = forms.ChoiceField(choices=((3, 'Verified'), (0, 'Rejected')), widget=forms.RadioSelect)

    class Meta:
        model = models.VerificationRequest
        fields = ('status', 'verification_comment', 'images')

class StaffFilterVerificationRequestForm(ModelForm):
    OS = forms.ChoiceField(choices=BLANK_CHOICE_DASH + list(models.OS_CHOICES), required=False)
    language = forms.ChoiceField(choices=BLANK_CHOICE_DASH + list(models.LANGUAGE_CHOICES), required=False)

    def __init__(self, *args, **kwargs):
        super(StaffFilterVerificationRequestForm, self).__init__(*args, **kwargs)
        self.fields['verified_by'].queryset = User.objects.filter(is_staff=True)
        self.fields['verified_by'].required = False
        self.fields['status'].required = False
        self.fields['status'].choices = BLANK_CHOICE_DASH + self.fields['status'].choices
        self.fields['verification'].required = False
        self.fields['verification'].help_text = None
        self.fields['allow_during_events'].help_text = None
        self.fields['allow_during_events'].label = 'Allowed us to verify them during events'

    class Meta:
        model = models.VerificationRequest
        fields = ('status', 'verified_by', 'verification', 'OS', 'language', 'allow_during_events')

class FilterSongForm(ModelForm):
    search = forms.CharField(required=False, label=_('Search'))
    ordering = forms.ChoiceField(choices=[
        ('latest', _('Latest unlocked songs')),
        ('name', _('Song name')),
        ('BPM', _('Beats per minute')),
        ('time', _('Song length')),
        ('rank', _('Rank to unlock song')),
        ('hard_notes', _('Notes in Hard song')),
        ('expert_notes', _('Notes in Expert song')),
    ], initial='latest', required=False, label=_('Ordering'))
    reverse_order = forms.BooleanField(initial=True, required=False, label=_('Reverse order'))
    is_daily_rotation = forms.NullBooleanField(required=False, label=_('Daily rotation'))
    is_event = forms.NullBooleanField(required=False, label=_('Event'))
    available = forms.NullBooleanField(required=False, label=_('Available'))

    def __init__(self, *args, **kwargs):
        super(FilterSongForm, self).__init__(*args, **kwargs)
        for field in self.fields.keys():
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label

    class Meta:
        model = models.Song
        fields = ('search', 'attribute', 'is_daily_rotation', 'is_event', 'available', 'ordering', 'reverse_order')

class FilterUserForm(ModelForm):
    search = forms.CharField(required=False, label=_('Search'))
    ordering = forms.ChoiceField(choices=[
        ('rank', _('Leaderboard')),
        ('owner__date_joined', _('New players')),
    ], initial='latest', required=False, label=_('Ordering'))
    reverse_order = forms.BooleanField(initial=True, required=False, label=_('Reverse order'))

    attribute = forms.ChoiceField(choices=(BLANK_CHOICE_DASH + list(models.ATTRIBUTE_CHOICES)), label=_('Attribute'), required=False)
    best_girl = ChoiceField(label=_('Best Girl'), choices=getGirls(), required=False)
    # location = forms.CharField(required=False, label=_('Location'))
    private = forms.NullBooleanField(required=False, label=_('Private Profile'))
    status = ChoiceField(label=_('Donators'), choices=(BLANK_CHOICE_DASH + list(models.STATUS_CHOICES)), required=False)
    with_friend_id = forms.NullBooleanField(required=True, label=string_concat(_('Friend ID'), ' (', _('specified'), ')'))
    center_attribute = forms.ChoiceField(choices=(BLANK_CHOICE_DASH + list(models.ATTRIBUTE_CHOICES)), label=string_concat(_('Center'), ': ', _('Attribute')), required=False)
    center_rarity = forms.ChoiceField(choices=(BLANK_CHOICE_DASH + list(models.RARITY_CHOICES)), label=string_concat(_('Center'), ': ', _('Rarity')), required=False)

    def __init__(self, *args, **kwargs):
        super(FilterUserForm, self).__init__(*args, **kwargs)
        for field in self.fields.keys():
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label
        self.fields['language'].choices = BLANK_CHOICE_DASH + self.fields['language'].choices
        self.fields['os'].choices = BLANK_CHOICE_DASH + self.fields['os'].choices
        self.fields['verified'].choices = BLANK_CHOICE_DASH + [(3, _('Only'))] + self.fields['verified'].choices
        del(self.fields['verified'].choices[-1])
        self.fields['verified'].initial = None
        self.fields['os'].initial = None
        self.fields['language'].initial = None
        del(self.fields['status'].choices[0])
        del(self.fields['status'].choices[0])
        self.fields['status'].choices = BLANK_CHOICE_DASH + [('only', _('Only'))] + self.fields['status'].choices
        #self.fields['status'].choices.insert(1, ('only', _('Only'))) this doesn't work i don't know why

    class Meta:
        model = models.Account
        fields = ('search', 'attribute', 'best_girl', 'private', 'status', 'language', 'os', 'verified', 'center_attribute', 'center_rarity', 'with_friend_id', 'accept_friend_requests', 'play_with', 'ordering', 'reverse_order')

# class TeamForm(ModelForm):
#     card0 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card1 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card2 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card3 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card4 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card5 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card6 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card7 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     card8 = OwnedCardModelChoiceField(queryset=models.OwnedCard.objects.all(), required=False)
#     class Meta:
#         model = models.Team
#         fields = ('name', 'card0', 'card1', 'card2', 'card3', 'card4', 'card5', 'card6', 'card7', 'card8')

# def getTeamForm(form, ownedcards):
#     for i in range(9):
#         print 'test'
#         setattr(form, 'card' + str(i), OwnedCardModelChoiceField(queryset=ownedcards, required=False))
#     return form

