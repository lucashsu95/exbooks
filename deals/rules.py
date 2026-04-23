import rules

# Predicates
@rules.predicate
def is_applicant(user, deal):
    return deal is not None and user == deal.applicant

@rules.predicate
def is_responder(user, deal):
    return deal is not None and user == deal.responder

@rules.predicate
def is_owner(user, deal):
    return deal is not None and user == deal.shared_book.owner

@rules.predicate
def is_keeper(user, deal):
    return deal is not None and user == deal.shared_book.keeper

@rules.predicate
def is_force_return_receiver(user, deal):
    from .services import deal_service
    return deal is not None and user == deal_service.get_force_return_receiver(deal)

@rules.predicate
def is_involved(user, deal):
    return is_applicant(user, deal) | is_responder(user, deal)

# Deal permissions
rules.add_perm('deals.can_accept_deal', is_responder)
rules.add_perm('deals.can_decline_deal', is_responder)
rules.add_perm('deals.can_cancel_deal', is_applicant)

rules.add_perm('deals.can_complete_meeting', is_involved)
rules.add_perm('deals.can_send_message', is_involved)
rules.add_perm('deals.can_rate_deal', is_involved)

# Extension permissions
rules.add_perm('deals.can_request_extension', is_applicant)

# For extensions, the object passed might be the Extension object or the Deal.
# The plan says "can_request_extension, can_approve_extension, etc."
# Let's create predicates for LoanExtension
@rules.predicate
def is_extension_applicant(user, extension):
    return extension is not None and user == extension.requested_by

@rules.predicate
def is_extension_reviewer(user, extension):
    return extension is not None and (user == extension.deal.shared_book.owner or user == extension.deal.shared_book.keeper)

rules.add_perm('deals.can_approve_extension', is_extension_reviewer)
rules.add_perm('deals.can_reject_extension', is_extension_reviewer)
rules.add_perm('deals.can_cancel_extension', is_extension_applicant)

# Return permissions
@rules.predicate
def is_return_confirmer(user, deal):
    return deal is not None and user == deal.responder

rules.add_perm('deals.can_confirm_return', is_return_confirmer)
rules.add_perm('deals.can_force_return', is_force_return_receiver)

# Upload photos
@rules.predicate
def can_upload_photos(user, deal):
    # Only keeper can upload photos
    return deal is not None and user == deal.shared_book.keeper

rules.add_perm('deals.can_upload_deal_photos', can_upload_photos)

@rules.predicate
def is_book_keeper(user, book):
    return book is not None and user == book.keeper

@rules.predicate
def is_book_owner(user, book):
    return book is not None and user == book.owner

rules.add_perm('deals.can_create_exception', is_book_keeper)
rules.add_perm('deals.can_resolve_exception', is_book_owner)
