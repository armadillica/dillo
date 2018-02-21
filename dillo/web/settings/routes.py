import logging
from flask import render_template
from flask_login import login_required, current_user
from pillar.web.settings import blueprint as blueprint_settings
from dillo.web.settings.forms import LinksListForm

log = logging.getLogger(__name__)


@blueprint_settings.route('/links', methods=['GET', 'POST'])
@login_required
def links():
    """Links settings.
    """
    form = LinksListForm()
    if form.validate_on_submit():
        for f in form.links:
            print(f.data)

    for e, v in form.errors.items():
        log.debug("Error validating field %s" % e)

    return render_template('users/settings/links.html', form=form, title='emails')
    # if current_user.has_role('protected'):
    #     return abort(404)  # TODO: make this 403, handle template properly
    # api = system_util.pillar_api()
    # user = User.find(current_user.objectid, api=api)
    #
    # # Force creation of settings for the user (safely remove this code once
    # # implemented on account creation level, and after adding settings to all
    # # existing users)
    # if not user.settings:
    #     user.settings = dict(email_communications=1)
    #     user.update(api=api)
    #
    # if user.settings.email_communications is None:
    #     user.settings.email_communications = 1
    #     user.update(api=api)
    #
    # # Generate form
    # form = forms.UserSettingsEmailsForm(
    #     email_communications=user.settings.email_communications)
    #
    # if form.validate_on_submit():
    #     try:
    #         user.settings.email_communications = form.email_communications.data
    #         user.update(api=api)
    #         flash("Profile updated", 'success')
    #     except sdk_exceptions.ResourceInvalid as e:
    #         message = json.loads(e.content)
    #         flash(message)
    #
    # return render_template('users/settings/emails.html', form=form, title='emails')
