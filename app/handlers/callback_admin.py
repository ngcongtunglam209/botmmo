"""
Admin callback dispatcher.
Routes administrative callbacks to specific handler services.

This file no longer contains monolithic business logic. Instead, it delegates
calls to services like admin_refund.py, admin_orders.py, admin_support.py, etc.
"""

async def handle_admin_callbacks(update, context, command):
    """
    Main entry point for administrative callbacks.
    Acts as a router delegating requests to specific modules.
    """
    query = update.callback_query
    user_id = update.effective_user.id

    # Menu & UI actions (no permissions check needed here if already checked in commands, but we enforce below anyway)
    if command.startswith("adm:"):
        await handle_admin_menu_callback(query, context)
        return True
    if command.startswith("adm_uo:"):
        if user_id != ADMIN_USER_ID:
            await safe_answer(query, "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> Bạn không có quyền!", show_alert=True)
            return True
        await handle_admin_user_orders_pagination(query, context)
        return True
    if command.startswith("adm_quick:"):
        if user_id != ADMIN_USER_ID:
            await safe_answer(query, "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> Bạn không có quyền!", show_alert=True)
            return True
        await handle_admin_quick_action(query, context)
        return True

    # Security Gate: enforce admin check for all administrative actions
    admin_only_prefixes = (
        'manual_done_', 'manual_refund_', 'manual_done:', 'manual_refund:',
        'approve_withdraw:', 'reject_withdraw:',
        'approve_warranty:', 'reject_warranty:',
        'admin_open_chat:', 'admin_close_chat:',
        'resend_link:', 'reject_expired:', 'reject_policy:',
        'warranty_done:', 'dismiss_report:', 'replace_auto:', 'replace_manual:',
        'admrf_f_', 'admrf_p_',
        'api_approve_', 'api_refund_', 'approve_api:', 'reject_api:',
        'complete_manual_', 'refund_manual_',
    )
    
    if command.startswith(admin_only_prefixes) and user_id != ADMIN_USER_ID:
        await safe_answer(query, "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> Bạn không có quyền thực hiện!", show_alert=True)
        return True

    if not _callback_requires_manual_answer(command):
        await safe_answer(query)

    # 1. Admin Refund Service
    if command.startswith(('admrf_f_', 'admrf_p_')):
        await handle_admin_refund(query, context, update)
        return True

    # 2. Admin Orders Service
    if command.startswith(('api_approve_', 'api_refund_')):
        await handle_api_order_approval(query, context, update)
        return True
    if command.startswith(('complete_manual_', 'refund_manual_')):
        await handle_manual_order_action(query, context, update)
        return True
    if command.startswith(('manual_done_', 'manual_refund_')):
        await handle_legacy_manual_done_refund(query, context, command)
        return True
    if command.startswith(('manual_done:', 'manual_refund:')):
        await handle_new_manual_done_refund(query, context, command)
        return True
    if command.startswith(('cancel_order:', 'cancel_payment_')):
        await handle_cancel_order_payment(query, context, command)
        return True

    # 3. Admin Withdrawals & API Registration Service
    if command.startswith(('approve_withdraw:', 'reject_withdraw:')):
        await handle_withdrawal_action(query, context, command, user_id)
        return True
    if command.startswith(('approve_api:', 'reject_api:')):
        await handle_api_registration_action(query, context, command, user_id)
        return True

    # 4. Admin Support Service
    if command.startswith('approve_warranty:'):
        await handle_warranty_approval(query, context, command)
        return True
    if command.startswith('reject_warranty:'):
        await handle_warranty_rejection(query, context, command)
        return True
    if command.startswith('admin_open_chat:'):
        await handle_admin_open_chat(query, context, command, user_id)
        return True
    if command.startswith('admin_close_chat:'):
        await handle_admin_close_chat(query, context, command)
        return True
    if command.startswith('resend_link:'):
        await handle_resend_link(query, context, command, user_id)
        return True
    if command.startswith(('reject_expired:', 'reject_policy:')):
        await handle_reject_report(query, context, command)
        return True
    if command.startswith('warranty_done:'):
        await handle_warranty_done(query, context, command, user_id)
        return True
    if command.startswith('dismiss_report:'):
        await handle_dismiss_report(query, context, command)
        return True
    if command.startswith('replace_auto:'):
        await handle_replace_auto(query, context, command)
        return True
    if command.startswith('replace_manual:'):
        await handle_replace_manual(query, context, command)
        return True

    return False
