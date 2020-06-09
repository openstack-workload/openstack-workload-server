
import stackconfig
import datetime
import os


class slog:
    fp = None
    fname = None

    def __init__(self):
        now = datetime.datetime.now()
        
        fdir = "{path}/tasks/{year}-{month:02}".format(
            path=stackconfig.STACKPATH_LOG,
            year=now.year,
            month=now.month
        )

        if not os.path.exists(fdir):
            os.makedirs(fdir)


        self.fname = "{fdir}/{year}-{month:02}-{day:02}-{hour:02}-{minute:02}.task".format(
            fdir=fdir,
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute
        )

        self.fp = open(self.fname, "w")

    def p(self, n, break_line=True):
        print(n)
        self.fp.write(n)
        if break_line == True:
            self.fp.write("\n")

    def close(self):
        self.fp.close()

    def logresult(self, result, host_old=None, host_new=None, vm=None):
        now = datetime.datetime.now()

        full = "{year}-{month:02}-{day:02}-{hour:02}-{minute:02} {result} vm {vm} from {host_old} to {host_new}".format(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            result=result,
            host_old=host_old,
            host_new=host_new,
            vm=vm
        )

        fname = "{path}/result/{year}-{month:02}-{day:02}".format(
            path=stackconfig.STACKPATH_LOG,
            year=now.year,
            month=now.month,
            day=now.day
        )

        f = open(fname, "a")
        f.write(full)
        f.write("\n")
        f.close()



"""slog = slog()
slog.p("foo")
slog.p("bar")
slog.p("\n\n")
slog.p("xxx")
slog.close()"""

