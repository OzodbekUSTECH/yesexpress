from institution.models import Institution
from order.models import Order, OrderStatusTimeline
from order.status_controller import update_order_status
import pytest
from unittest import mock
from django.utils import timezone


@pytest.fixture
def order(db, mocker):
    institution = Institution.objects.create(
        name="Test Institution",
        phone_number="+998901234567",
        type="restaurant",
    )
    order = Order.objects.create(
        institution=institution,
        status="created",
        delivery_price=0,
        total_price=10000,
        payment_type="cash"
    )
    
    OrderStatusTimeline.objects.create(order=order)


    # Notifications
    mocker.patch('order.services.notify_courier')
    mocker.patch('order.services.notify_operator')
    mocker.patch('order.services.notify_institution')
    mocker.patch('order.utils.send_notification')
    mocker.patch('order.utils.send_message')
    return order


def test_update_order_status_to_accepted_cash(order):
    result = update_order_status(order, 'accepted', preparing_time=15)

    assert result is True
    assert order.status == 'accepted'
    assert order.preparing_time == 15
    assert order.timeline is not None


def test_update_order_status_to_accepted_payme_success(order, mocker):
    order.payment_method = 'payme'
    order.save()

    mocker.patch('delivery.payments.payme', return_value={'status': 'success'})

    result = update_order_status(order, 'accepted')

    assert result is True
    assert order.status == 'accepted'


def test_update_order_status_to_accepted_payme_error(order, mocker):
    order.payment_method = 'payme'
    order.save()

    mocker.patch('delivery.payments.payme', return_value={
        'status': 'error', 'message': 'Invalid card'
    })

    result = update_order_status(order, 'accepted')

    assert result is True
    assert order.status == 'rejected'


def test_update_order_status_same_status(order):
    order.status = 'accepted'
    order.save()

    result = update_order_status(order, 'accepted')

    assert result is False


def test_update_order_status_to_rejected(order):
    result = update_order_status(order, 'rejected')

    assert result is True
    assert order.status == 'rejected'
    assert order.timeline.rejected_at is not None


def test_update_order_status_to_ready(order):
    result = update_order_status(order, 'ready')

    assert result is True
    assert order.status == 'ready'
    assert order.timeline.ready_at is not None


def test_update_order_status_to_shipped(order):
    result = update_order_status(order, 'shipped')

    assert result is True
    assert order.status == 'shipped'
    assert order.timeline.shipped_at is not None


def test_update_order_status_to_closed(order):
    order.status = 'ready'
    order.is_paid = False
    order.save()

    result = update_order_status(order, 'closed')

    assert result is True
    assert order.status == 'closed'
    assert order.timeline.closed_at is not None
    assert order.is_paid is True
    assert order.institution.balance_set.exists()


def test_update_order_status_notifications(order, mocker):
    notify_courier = mocker.patch('delivery.services.notify_courier')
    notify_operator = mocker.patch('delivery.services.notify_operator')
    notify_institution = mocker.patch('delivery.services.notify_institution')

    update_order_status(order, 'accepted', preparing_time=10)

    notify_courier.assert_called_once_with(order)
    notify_operator.assert_called_once_with(order)
    notify_institution.assert_called_once_with(order)
