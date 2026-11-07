"""Offline regression tests for Italian listing text and cross-portal duplicates."""
import unittest
from case_parser import price_from, number, address_from, pick_address, address_parts, match


class PriceRegressionTests(unittest.TestCase):
    def test_price_next_to_civic_number(self):
        self.assertEqual(price_from('Via Esempio 10 € 79.000'), 79000)
        self.assertEqual(price_from('Via Roma 5 € 79.000 70 m² 3 locali'), 79000)

    def test_reduced_price_and_installment(self):
        self.assertEqual(price_from('€ 85.000 → € 79.000'), 79000)
        self.assertEqual(price_from('85.000 € → 79.000 €'), 79000)
        self.assertEqual(price_from('Rata € 350/mese. Prezzo € 79.000'), 79000)
        self.assertEqual(price_from('Prezzo € 79.000. Rata € 350 al mese'), 79000)

    def test_csv_numbers(self):
        for raw in ('79000.0', '79000,0', '79.000,00', '79,000.00', '79.000', '79000'):
            with self.subTest(raw=raw):
                self.assertEqual(number(raw), 79000)
        self.assertIsNone(number('n.d.'))


class AddressRegressionTests(unittest.TestCase):
    def test_address_stops_before_price_and_floor(self):
        self.assertEqual(address_from('Via Roma 5 € 79.000 70 m² 3 locali'), 'Via Roma 5')
        self.assertEqual(address_from('Via Roma, 10 - 3° piano'), 'Via Roma, 10')
        self.assertEqual(address_parts('via Roma, 10 - 3° piano'), ('via', 'roma', '10'))
        self.assertEqual(pick_address('Bilocale in Via Roma', 'Bilocale Via Roma 10 € 79.000'),
                         'Via Roma 10')

    def test_exact_address_and_distinct_street_types(self):
        a = dict(city='Reggio Emilia', site='casa.it', url='https://www.casa.it/immobili/111/',
                 title='Bilocale Via Roma 10', address='Via Roma 10', price_eur='79000.0',
                 area_m2='70.0')
        b = dict(a, site='idealista.it', url='https://www.idealista.it/immobile/222/',
                 address='via Roma, 10 - 3° piano')
        self.assertEqual(match(a, b)[0], 'MATCH')
        self.assertEqual(match(a, dict(b, address='Via Roma 12'))[0], 'NONE')
        self.assertEqual(match(a, dict(b, address='Viale Roma 10'))[0], 'NONE')
        self.assertEqual(match(a, dict(b, address='Via Roma'))[0], 'REVIEW')
        self.assertEqual(match(a, dict(b, city='Modena'))[0], 'NONE')


if __name__ == '__main__':
    unittest.main()
