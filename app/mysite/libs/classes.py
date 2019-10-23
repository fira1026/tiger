# -*- coding: utf-8 -*-
"""Schedules define the intervals at which periodic tasks run."""
from __future__ import absolute_import, unicode_literals
from datetime import datetime
from celery.schedules import crontab, cronfield
from celery.utils.time import ffwd
from celery.utils.collections import AttributeDict
from bisect import bisect, bisect_left


CRON_REPR = '''\
<crontab: {0._orig_second} {0._orig_minute} {0._orig_hour} {0._orig_day_of_week} \
{0._orig_day_of_month} {0._orig_month_of_year} (s/m/h/d/dM/MY)>\
'''


class ExtendedCrontab(crontab):
    '''
    custom crontab to support 'seconds'
    '''

    def __init__(self, second=0, minute='*', hour='*', day_of_week='*',
                 day_of_month='*', month_of_year='*', **kwargs):
        self._orig_second = cronfield(second)
        self._orig_minute = cronfield(minute)
        self._orig_hour = cronfield(hour)
        self._orig_day_of_week = cronfield(day_of_week)
        self._orig_day_of_month = cronfield(day_of_month)
        self._orig_month_of_year = cronfield(month_of_year)
        self._orig_kwargs = kwargs
        self.hour = self._expand_cronspec(hour, 24)
        self.minute = self._expand_cronspec(minute, 60)
        self.second = self._expand_cronspec(second, 60)
        self.day_of_week = self._expand_cronspec(day_of_week, 7)
        self.day_of_month = self._expand_cronspec(day_of_month, 31, 1)
        self.month_of_year = self._expand_cronspec(month_of_year, 12, 1)
        super(crontab, self).__init__(**kwargs)

    def _delta_to_next(self, last_run_at, next_hour, next_minute, next_second):
        """Find next delta.

        Takes a :class:`~datetime.datetime` of last run, next minute and hour,
        and returns a :class:`~celery.utils.time.ffwd` for the next
        scheduled day and time.

        Only called when ``day_of_month`` and/or ``month_of_year``
        cronspec is specified to further limit scheduled task execution.
        """
        datedata = AttributeDict(year=last_run_at.year)
        days_of_month = sorted(self.day_of_month)
        months_of_year = sorted(self.month_of_year)

        def day_out_of_range(year, month, day):
            try:
                datetime(year=year, month=month, day=day)
            except ValueError:
                return True
            return False

        def roll_over():
            for _ in range(2000):
                flag = (datedata.dom == len(days_of_month) or
                        day_out_of_range(datedata.year,
                                         months_of_year[datedata.moy],
                                         days_of_month[datedata.dom]) or
                        (self.maybe_make_aware(datetime(datedata.year,
                         months_of_year[datedata.moy],
                         days_of_month[datedata.dom])) < last_run_at))

                if flag:
                    datedata.dom = 0
                    datedata.moy += 1
                    if datedata.moy == len(months_of_year):
                        datedata.moy = 0
                        datedata.year += 1
                else:
                    break
            else:
                # Tried 2000 times, we're most likely in an infinite loop
                raise RuntimeError('unable to rollover, '
                                   'time specification is probably invalid')

        if last_run_at.month in self.month_of_year:
            datedata.dom = bisect(days_of_month, last_run_at.day)
            datedata.moy = bisect_left(months_of_year, last_run_at.month)
        else:
            datedata.dom = 0
            datedata.moy = bisect(months_of_year, last_run_at.month)
            if datedata.moy == len(months_of_year):
                datedata.moy = 0
        roll_over()

        while 1:
            th = datetime(year=datedata.year,
                          month=months_of_year[datedata.moy],
                          day=days_of_month[datedata.dom])
            if th.isoweekday() % 7 in self.day_of_week:
                break
            datedata.dom += 1
            roll_over()

        return ffwd(year=datedata.year,
                    month=months_of_year[datedata.moy],
                    day=days_of_month[datedata.dom],
                    hour=next_hour,
                    minute=next_minute,
                    second=next_second,
                    microsecond=0)

    def __repr__(self):
        return CRON_REPR.format(self)

    def __reduce__(self):
        return (self.__class__, (self._orig_second,
                                 self._orig_minute,
                                 self._orig_hour,
                                 self._orig_day_of_week,
                                 self._orig_day_of_month,
                                 self._orig_month_of_year), self._orig_kwargs)

    def remaining_delta(self, last_run_at, tz=None, ffwd=ffwd):
        tz = tz or self.tz
        last_run_at = self.maybe_make_aware(last_run_at)
        now = self.maybe_make_aware(self.now())
        dow_num = last_run_at.isoweekday() % 7  # Sunday is day 0, not day 7
        execute_this_date = (last_run_at.month in self.month_of_year and
                             last_run_at.day in self.day_of_month and
                             dow_num in self.day_of_week)

        execute_this_hour = (execute_this_date and
                             last_run_at.day == now.day and
                             last_run_at.month == now.month and
                             last_run_at.year == now.year and
                             last_run_at.hour in self.hour and
                             last_run_at.minute < max(self.minute))
        execute_this_minute = (last_run_at.minute in self.minute and
                               last_run_at.second < max(self.second))
        if execute_this_minute:
            next_second = min(second for second in self.second
                              if second > last_run_at.second)
            delta = ffwd(second=next_second, microsecond=0)
        else:
            if execute_this_hour:
                next_minute = min(minute for minute in self.minute
                                  if minute > last_run_at.minute)
                next_second = min(self.second)
                delta = ffwd(minute=next_minute, second=next_second, microsecond=0)
            else:
                next_minute = min(self.minute)
                next_second = min(self.second)
                execute_today = (execute_this_date and
                                 last_run_at.hour < max(self.hour))

                if execute_today:
                    next_hour = min(hour for hour in self.hour
                                    if hour > last_run_at.hour)
                    delta = ffwd(hour=next_hour, minute=next_minute,
                                 second=next_second, microsecond=0)
                else:
                    next_hour = min(self.hour)
                    all_dom_moy = (self._orig_day_of_month == '*' and
                                   self._orig_month_of_year == '*')
                    if all_dom_moy:
                        next_day = min([day for day in self.day_of_week
                                        if day > dow_num] or self.day_of_week)
                        add_week = next_day == dow_num

                        delta = ffwd(weeks=add_week and 1 or 0,
                                     weekday=(next_day - 1) % 7,
                                     hour=next_hour,
                                     minute=next_minute,
                                     second=next_second,
                                     microsecond=0)
                    else:
                        delta = self._delta_to_next(last_run_at,
                                                    next_hour, next_minute,
                                                    next_second)
        return self.to_local(last_run_at), delta, self.to_local(now)

    def __eq__(self, other):
        if isinstance(other, crontab):
            return (
                other.month_of_year == self.month_of_year and
                other.day_of_month == self.day_of_month and
                other.day_of_week == self.day_of_week and
                other.hour == self.hour and
                other.minute == self.minute and
                other.second == self.second and
                super(crontab, self).__eq__(other)
            )
        return NotImplemented
