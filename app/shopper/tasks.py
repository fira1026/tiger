import logging

from mysite.celery import app
from mysite.libs.classes import ExtendedCrontab
from mysite.telegram_bot import send_telegram_notify
from django.db.models import Sum, Count

from shopper.models import Product, Order, Shop

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Handler class for create_daily_report task.
class CreateDailyReportTask(app.Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super(CreateDailyReportTask, self).on_failure(exc, task_id, args, kwargs, einfo)

        telgram_msgs = []
        msg = \
            f'創建每日報表發生錯誤。請檢查 !! \n' \
            f'Task ID: {task_id} \n' \
            f'Error: {einfo} \n' \
            f"{'-' * 80 }"

        logger.error(f'Create schedule task encountered failure. msg={msg}')

        telgram_msgs.append(msg)
        send_telegram_notify(telgram_msgs)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # every 5am.
    sender.add_periodic_task(ExtendedCrontab(hour=5, minute=0),
                             create_daily_report.s(),
                             queue='periodic_queue',
                             name='creates daily report for today')


@app.task(name='create_daily_report', base=CreateDailyReportTask,
          time_limit=600, soft_time_limit=570)
def create_daily_report():

    telgram_msgs = []


    query = Order.objects.exclude(status__in=[Order.FAIL, Order.CANCEL])
    infos = query. \
        values('product__shop_id'). \
        annotate(total_order_price=Sum('total_price'),
                 total_qty=Sum('qty'),
                 total_order_count=Count('id'))

    # 根據訂單記錄算出各個館別的1.總銷售金額 2.總銷售數量 3.總訂單數量
    for info in infos:
        msg = \
            f"館別: {info['product__shop_id']} \n" \
            f"總訂單數量: {info['total_order_count']} \n" \
            f"總銷售數量: {info['total_qty']} \n" \
            f"總銷售金額: {info['total_order_price']} \n" \
            f"{'-' * 80 }"
        telgram_msgs.append(msg)

    if telgram_msgs != []:
        send_telegram_notify(telgram_msgs)
