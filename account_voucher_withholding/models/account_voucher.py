# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp


class account_voucher(models.Model):

    _inherit = "account.voucher"

    withholding_ids = fields.One2many(
        'account.voucher.withholding',
        'voucher_id',
        string='Withholdings',
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]}
        )

    @api.one
    @api.onchange(
        'withholding_ids',
        )
    def onchange_withholdings(self):
        """We force the update of paylines and amount"""
        self._get_paylines_amount()
        self._get_amount()

    @api.multi
    def get_paylines_amount(self):
        res = super(account_voucher, self).get_paylines_amount()
        for key, value in res.iteritems():
            new_val = value
            new_val += sum(x.amount for x in self.withholding_ids)
            res[key] = new_val
        return res

    @api.model
    def paylines_moves_create(
            self, voucher, move_id, company_currency, current_currency):
        paylines_total = super(account_voucher, self).paylines_moves_create(
            voucher, move_id, company_currency, current_currency)
        withholding_total = self.create_withholding_lines(
            voucher, move_id, company_currency, current_currency)
        return paylines_total + withholding_total

    # TODO ver si en vez de usar api.model usamos self y no pasamos el voucher
    # TODO ver que todo esto solo funcione en payment y receipts y no en sale y purchase
    @api.model
    def create_withholding_lines(
            self, voucher, move_id, company_currency, current_currency):
        move_lines = self.env['account.move.line']
        withholding_total = 0.0
        for line in voucher.withholding_ids:
            name = '%s: %s' % (line.tax_withholding_id.name, line.name)
            payment_date = False
            amount = line.amount
            if voucher.type == 'receipt':
                account = line.tax_withholding_id.account_receipt_id
            elif voucher.type == 'payment':
                account = line.tax_withholding_id.account_payment_id
            partner = voucher.partner_id
            move_line = move_lines.create(
                self.prepare_move_line(
                    voucher, amount, move_id, name, company_currency,
                    current_currency, payment_date, account, partner)
                    )
            withholding_total += move_line.debit - move_line.credit
        return withholding_total
