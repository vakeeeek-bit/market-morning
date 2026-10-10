import unittest
from scripts.publication_observations import validate_observations, ESSENTIAL, SECTORS

def valid_market():
    rows={key:dict(price=1,market_date='2026-10-09') for key in ESSENTIAL}
    for key in SECTORS: rows['sector_'+key]=dict(price=1,market_date='2026-10-09')
    for key in ('gold','copper','wti','brent'):
        rows[key]['instrument']=dict(verification_status='verified',exchange='NYMEX',contract_month='2026-11',value_kind='daily_close',basis_time='2026-10-09T17:00:00-04:00',source_url='https://example.org/report',market_date='2026-10-09')
    return dict(markets=rows)

class PublicationObservationTests(unittest.TestCase):
    def test_unknown_month_blocks_even_when_prices_present(self):
        m=valid_market();m['markets']['brent']['instrument']['contract_month']=''
        self.assertTrue(any('brent' in x for x in validate_observations(m)))
    def test_three_missing_sector_observations_block(self):
        m=valid_market()
        for k in SECTORS[:3]:m['markets']['sector_'+k]['price']=None
        self.assertTrue(any('3系列' in x for x in validate_observations(m)))
    def test_current_contract_cannot_certify_other_observation_date(self):
        m=valid_market();m['markets']['gold']['instrument']['market_date']='2026-10-08'
        self.assertTrue(any('対応' in x for x in validate_observations(m)))
    def test_naive_futures_time_cannot_be_admitted(self):
        m=valid_market();m['markets']['wti']['instrument']['basis_time']='2026-10-09T17:00:00'
        self.assertTrue(any('タイムゾーン' in x for x in validate_observations(m)))
    def test_confirmed_observations_pass(self):
        self.assertEqual([],validate_observations(valid_market()))
