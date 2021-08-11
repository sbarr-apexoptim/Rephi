import pandas as pd
import numpy as np

def amortization(name, sp, ir, term, extra, starting_equity, total_interest_paid=0, starting_date=pd.Timestamp(2018, 7, 1)):
    ir = float(ir)
    term = float(term)
    sp = float(sp)
    mp = sp * (((ir / 12.0) * (1.0 + (ir / 12.0))** term) / (((1.0 + (ir / 12.0))**term) - 1.0))

    mpa = mp + extra

    extra_paid = 0.0
    interest = sp * (ir / 12.0)
    tip = total_interest_paid
    principal = mpa - interest
    equity = starting_equity
    balance = sp
    month = 1
    year = 1
    date = starting_date
    date_a = []
    year_a = []
    month_a = []
    balance_a = []
    principal_a = []
    interest_a = []
    tip_a = []
    equity_a = []
    mpa_a = []
    extra_paid_a = []
    nmonths = 0
    date_a.append(date)
    year_a.append(year)
    month_a.append(month)
    balance_a.append(balance)
    principal_a.append(principal)
    interest_a.append(interest)
    tip_a.append(tip)
    equity_a.append(equity)
    mpa_a.append(mp)
    extra_paid_a.append(extra_paid)
    nmonths = 1
    date += pd.DateOffset(months=1)
    while balance > 1.0e-6:
        interest = balance * (ir / 12.0)
        tip += interest
        principal = mpa - interest
        if balance > principal:
            balance = balance - principal
        else:
            balance = 0.0
        equity = equity + principal
        if equity > sp + starting_equity:
          equity = sp + starting_equity
        extra_paid = extra_paid + extra
        date_a.append(date)
        year_a.append(year)
        month_a.append(month)
        balance_a.append(balance)
        principal_a.append(principal)
        interest_a.append(interest)
        tip_a.append(tip)
        equity_a.append(equity)
        mpa_a.append(mp)
        extra_paid_a.append(extra_paid)
        nmonths += 1
        month = month + 1
        if month % 13 == 0:
            year = year + 1
            month = 1

        date += pd.DateOffset(months=1)

    data = pd.DataFrame(data={"Date": date_a,
                              "%s_Balance" % (name): balance_a,
                              "%s_Principal" % (name): principal_a,
                              "%s_Interest" % (name): interest_a,
                              "%s_TIP" % (name): tip_a,
                              "%s_Equity" % (name): equity_a,
                              "%s_MPA"%(name): mpa_a,
                              # "%s_Extra Paid"%(name): extra_paid_a
                              })

    #data.index = np.arange(nmonths) + 1
    data.index = np.arange(nmonths)

    return data

def get_mortgage_data(principal, interest_rate, extra, term, start_date, refi_principal, refi_interest_rate, refi_term, refi_date, lender_fees, iopt=False):
    base_payoff = []
    refi_payoff = []
    start_date = pd.Timestamp(start_date)
    refi_date = pd.Timestamp(refi_date)

    if pd.isnull(start_date):
      start_date = base_start_date
    if pd.isnull(refi_date):
      refi_date = base_refi_date

    start_year = start_date.year
    start_month = start_date.month
    refi_year = refi_date.year
    refi_month = refi_date.month
    start_date = pd.Timestamp(start_year, start_month, 1)
    refi_date = pd.Timestamp(refi_year, refi_month, 1)

    mortgages = amortization("m0",
                             principal,
                             interest_rate,
                             term,
                             0.0,
                             0.0,
                             0.0,
                             start_date)
    pi = mortgages["m0_MPA"].iloc[0]
    base_payoff.append(mortgages.index[-1])
    r = amortization("r0",
                     #principal -
                     #mortgages[mortgages["Date"] == refi_date]["m0_Equity"].iloc[0],
                     refi_principal,
                     refi_interest_rate,
                     refi_term,
                     0.0,
                     mortgages[mortgages["Date"] == refi_date]["m0_Equity"].iloc[0],
                     mortgages[mortgages["Date"] == refi_date]["m0_TIP"].iloc[0],
                     refi_date)
    rpi = r["r0_MPA"].iloc[0]
    refi_payoff.append(r.index[-1])
    mortgages = mortgages.merge(r, how="left", on="Date")
    me = amortization("me",
                     principal,
                     interest_rate,
                     term,
                     extra,
                     0.0,
                     0.0,
                     start_date)
    #base_payoff.append(me.index[-1])
    try:
      re = amortization("re",
                       refi_principal,
                       #principal - me[me["Date"] == refi_date]["me_Equity"].iloc[0],
                       refi_interest_rate,
                       refi_term,
                       extra,
                       me[me["Date"] == refi_date]["me_Equity"].iloc[0],
                       me[me["Date"] == refi_date]["me_TIP"].iloc[0],
                       refi_date)
    except:
      re = []
    #refi_payoff.append(re.index[-1])
    #mortgages = mortgages.merge(me, how="left", on="Date")
    #mortgages = mortgages.merge(re, how="left", on="Date")
    mortgages = mortgages.merge(me, how="outer", on="Date")
    mortgages = mortgages.merge(re, how="outer", on="Date")
    if iopt == True:
      for n in range(10):
          m = amortization("m%d" % (n + 1),
                           principal,
                           interest_rate,
                           term,
                           float(n + 1) * 100.0,
                           0.0,
                           0.0,
                           start_date)
          base_payoff.append(m.index[-1])
          try:
            r = amortization("r%d" % (n + 1),
                             refi_principal,
                             #principal -
                             #m[m["Date"] == refi_date]["m%d_Equity" %
                             #                              (n + 1)].iloc[0],
                             refi_interest_rate,
                             refi_term,
                             float(n + 1) * 100.0,
                             m[m["Date"] == refi_date]["m%d_Equity" %
                                                           (n + 1)].iloc[0],
                             m[m["Date"] == refi_date]["m%d_TIP" %
                                                           (n + 1)].iloc[0],
                             refi_date)
            refi_payoff.append(r.index[-1])
          except:
            continue
          mortgages = mortgages.merge(m, how="left", on="Date")
          mortgages = mortgages.merge(r, how="left", on="Date")

    return mortgages, base_payoff, refi_payoff, pi, rpi
