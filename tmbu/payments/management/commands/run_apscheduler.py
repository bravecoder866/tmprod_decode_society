# For usaged-based subscription
#from django.conf import settings
#from apscheduler.schedulers.blocking import BlockingScheduler
#from apscheduler.triggers.cron import CronTrigger
#from django.core.management.base import BaseCommand
#from django_apscheduler.jobstores import DjangoJobStore
#from django_apscheduler.models import DjangoJobExecution
#from django_apscheduler import util
#from apscheduler.executors.pool import ThreadPoolExecutor
#from payments.views import report_usage_for_all_users
#import logging

#logger = logging.getLogger(__name__)



#@util.close_old_connections
#def delete_old_job_executions(max_age=604_800):  #The maximum length of time. Defaults to 7 days.
#  DjangoJobExecution.objects.delete_old_job_executions(max_age)


#class Command(BaseCommand):
#  help = "Runs APScheduler."

#  def handle(self, *args, **options):
#    scheduler = BlockingScheduler(
#            timezone=settings.TIME_ZONE,
#            executors={"default": ThreadPoolExecutor(max_workers=1)},
#            job_defaults={"coalesce": False, "max_instances": 1},
#            )
            
#    scheduler.add_jobstore(DjangoJobStore(), "default")

#    scheduler.add_job(
#      report_usage_for_all_users,
#      trigger=CronTrigger(day=1, hour=0, minute=0),  # 00:00 on 1st day of every month
#      id="report_usage_for_all_users",  # The `id` assigned to each job MUST be unique
#      max_instances=1,
#      replace_existing=True,
#    )
#    logger.info("Added job 'report_usage_for_all_users'.")

#    scheduler.add_job(
#      delete_old_job_executions,
#      trigger=CronTrigger(
#        day=14, hour=0, minute=0
#      ),  
#      id="delete_old_job_executions",
#      max_instances=1,
#      replace_existing=True,
#    )
#    logger.info(
#      "Added weekly job: 'delete_old_job_executions'."
#    )

#    try:
#      logger.info("Starting scheduler...")
#      scheduler.start()
#    except KeyboardInterrupt:
#     logger.info("Stopping scheduler...")
#     scheduler.shutdown()
#     logger.info("Scheduler shut down successfully!")