from django.db.models import Sum, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import mixins, viewsets, renderers

from shopper.utils import vip_required, check_stock
from shopper.models import Order, Product
from shopper.serializer import OrderSerializer, ProductSerializer



class ProductViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    model = Product
    serializer_class = ProductSerializer
    renderer_classes = renderers.JSONRenderer


class OrderViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   mixins.UpdateModelMixin,
                   viewsets.GenericViewSet):
    '''
    For audit reason, we never delete order records. If a order need be canceled,
    Then the Order.status needs to be set to CANCEL, hence an update is issued.
    '''

    model = Order
    serializer_class = OrderSerializer
    renderer_classes = renderers.JSONRenderer

    def get_queryset(self):

        try:
            queryset = \
                Order.objects.all().select_related(
                    'product').order_by('-created_at')
        except:
            queryset = Order.objects.none()

        return queryset

    # TODO: add cache_response decorator
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        paginated_queryset = self.paginate_queryset(queryset)
        if paginated_queryset is not None:
            serializer = self.get_serializer(paginated_queryset, many=True)
            response = self.get_paginated_response(serializer.data)
            return response

        serializer = self.get_serializer(queryset, many=True)
        data = {'orders': serializer.data}
        return Response(data)

    @check_stock
    @vip_required
    def create(self, request, *args, **kwargs):
        ret = super().create(self, request, *args, **kwargs)
        return ret

    # To cancel an order, we use update() but not destroy().
    def update(self, request, *args, **kwargs):
        return super().update(self, request, *args, **kwargs)


@csrf_exempt
@api_view(['GET'])
@permission_classes([])
def get_top_3_products(request):
    '''
    Based on the total qty in orders to calculate the 3 most hot products.
    '''
    top_count = 3

    # Status in Fail and Cancel should be excluded.
    hot_products = list(
        Order.objects.filter(
            order_status__in=[Order.SUCCESS, Order.PAYMENT_PENDING, Order.NOT_IN_STOCK]
        ).values('product').annotate(total_qty=Sum('qty')
        ).values_list('product__id', flat=True
        ).order_by('-total_qty')[:top_count]
    )
    response = []
    for rank, product_id in enumerate(hot_products):

        response.append(
            {
                'rank': rank + 1,
                'product_id': product_id
            }
        )
    return JsonResponse(response, status=200)
