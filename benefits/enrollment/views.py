"""
The enrollment application: view definitions for the benefits enrollment flow.
"""
import logging

from django.conf import settings
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import decorator_from_middleware
from django.utils.translation import pgettext, gettext as _

from benefits.core import models, session, viewmodels
from benefits.core.middleware import EligibleSessionRequired, VerifierSessionRequired, pageview_decorator
from . import api, forms


logger = logging.getLogger(__name__)


def _index(request):
    """Helper handles GET requests to enrollment index."""
    agency = session.agency(request)

    tokenize_button = "tokenize_card"
    tokenize_retry_form = forms.CardTokenizeFailForm("enrollment:retry")
    tokenize_success_form = forms.CardTokenizeSuccessForm(auto_id=True, label_suffix="")

    page = viewmodels.Page(
        title=_("enrollment.pages.index.title"),
        content_title=_("enrollment.pages.index.content_title"),
        icon=viewmodels.Icon("idcardcheck", pgettext("image alt text", "core.icons.idcardcheck")),
        paragraphs=[_("enrollment.pages.index.p[0]"), _("enrollment.pages.index.p[1]"), _("enrollment.pages.index.p[2]")],
        classes="text-lg-center",
        forms=[tokenize_retry_form, tokenize_success_form],
        buttons=[
            viewmodels.Button.primary(
                text=_("enrollment.buttons.payment_partner"), id=tokenize_button, url=f"#{tokenize_button}"
            ),
        ],
    )
    context = {}
    context.update(page.context_dict())

    # add agency details
    agency_vm = viewmodels.TransitAgency(agency)
    context.update(agency_vm.context_dict())

    # and payment processor details
    processor_vm = viewmodels.PaymentProcessor(
        model=agency.payment_processor,
        access_token_url=reverse("enrollment:token"),
        element_id=f"#{tokenize_button}",
        color="#046b99",
        name=f"{agency.long_name} {_('partnered with')} {agency.payment_processor.name}",
    )
    context.update(processor_vm.context_dict())
    logger.warning(f"card_tokenize_url: {context['payment_processor'].card_tokenize_url}")

    # the tokenize form URLs are injected to page-generated Javascript
    context["forms"] = {
        "tokenize_retry": reverse(tokenize_retry_form.action_url),
        "tokenize_success": reverse(tokenize_success_form.action_url),
    }

    return TemplateResponse(request, "enrollment/index.html", context)


def _enroll(request):
    """Helper calls the enrollment APIs."""
    logger.debug("Read tokenized card")
    form = forms.CardTokenizeSuccessForm(request.POST)
    if not form.is_valid():
        raise Exception("Invalid card token form")
    card_token = form.cleaned_data.get("card_token")

    eligibility = session.eligibility(request)
    if eligibility:
        logger.debug(f"Session contains an {models.EligibilityType.__name__}")
    else:
        raise Exception("Session contains no eligibility information")

    agency = session.agency(request)

    response = api.Client(agency).enroll(card_token, eligibility.group_id)

    if response.success:
        return success(request)
    else:
        raise Exception("Updated customer_id does not match enrolled customer_id")


@decorator_from_middleware(EligibleSessionRequired)
def token(request):
    """View handler for the enrollment auth token."""
    if not session.enrollment_token_valid(request):
        agency = session.agency(request)
        response = api.Client(agency).access_token()
        session.update(request, enrollment_token=response.access_token, enrollment_token_exp=response.expiry)

    data = {"token": session.enrollment_token(request)}

    return JsonResponse(data)


@decorator_from_middleware(EligibleSessionRequired)
def index(request):
    """View handler for the enrollment landing page."""
    session.update(request, origin=reverse("enrollment:index"))

    if request.method == "POST":
        response = _enroll(request)
    else:
        response = _index(request)

    return response


@decorator_from_middleware(EligibleSessionRequired)
def retry(request):
    """View handler for a recoverable failure condition."""
    if request.method == "POST":
        form = forms.CardTokenizeFailForm(request.POST)
        if form.is_valid():
            agency = session.agency(request)
            page = viewmodels.Page(
                title=_("enrollment.pages.retry.title"),
                icon=viewmodels.Icon("bankcardquestion", pgettext("image alt text", "core.icons.bankcardquestion")),
                content_title=_("enrollment.pages.retry.title"),
                paragraphs=[_("enrollment.pages.retry.p[0]")],
                buttons=viewmodels.Button.agency_contact_links(agency),
            )
            page.buttons.append(viewmodels.Button.primary(text=_("core.buttons.retry"), url=session.origin(request)))
            return TemplateResponse(request, "enrollment/retry.html", page.context_dict())
        else:
            raise Exception("Invalid retry submission.")
    else:
        raise Exception("This view method only supports POST.")


@pageview_decorator
@decorator_from_middleware(VerifierSessionRequired)
def success(request):
    """View handler for the final success page."""
    request.path = "/enrollment/success"
    session.update(request, origin=reverse("enrollment:success"))
    verifier = session.verifier(request)

    if verifier.requires_authentication:
        if settings.OAUTH_CLIENT_NAME is None:
            raise Exception("EligibilityVerifier requires authentication, but OAUTH_CLIENT_NAME is None")

        if session.logged_in(request):
            button = viewmodels.Button.logout()
            page = viewmodels.Page(
                title=_("enrollment.pages.success.title"),
                icon=viewmodels.Icon("bankcardcheck", pgettext("image alt text", "core.icons.bankcardcheck")),
                content_title=_("enrollment.pages.success.content_title"),
                button=button,
                classes="logged-in",
            )
        else:
            page = viewmodels.Page(
                title=_("enrollment.pages.success.title"),
                content_title=_("enrollment.pages.success.logout.title"),
                classes="logged-out",
            )
    else:
        page = viewmodels.Page(
            title=_("enrollment.pages.success.title"),
            content_title=_("enrollment.pages.success.content_title"),
            icon=viewmodels.Icon("bankcardcheck", pgettext("image alt text", "core.icons.bankcardcheck")),
        )

    help_link = reverse("core:help")
    context_dict = {**page.context_dict(), **{"help_link": help_link}}

    return TemplateResponse(request, "enrollment/success.html", context_dict)
