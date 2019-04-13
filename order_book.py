import math
import os
import random
import re
import sys

import logging
import bisect
from decimal import Decimal
from collections import namedtuple

# Complete the 'solve' function below.

BUY_ORDER_PRICES = []  # Ascending list of Open Buy Limit Order prices
BUY_ORDER_BOOK = {}  # { Price : [ (Time, ClientID, Quantity) ] }

SELL_ORDER_PRICES = []  # Ascending list of Open Sell Limit Order prices
SELL_ORDER_BOOK = {}  # { Price : [ (Time, ClientID, Quantity) ] }

EXECUTED_ORDERS = []  # [  ( Time, ClientID1, ClientID2, Price, Quantity ) ]


def add_order_to_book(order):
    # Ensure only limit order get added to Order BUY_ORDER_BOOK
    if order.Type != 'l':
        logging.warning("Order at %s is not a limit order!" % order.Time)
        return
    order_book_entry = (order.Time, order.ClientID, order.Quantity)
    # Choose correct order book
    order_book = BUY_ORDER_BOOK if order.BuySell == 'b' else SELL_ORDER_BOOK
    order_book_prices = BUY_ORDER_PRICES if order.BuySell == 'b' else SELL_ORDER_PRICES
    if order.Price in order_book_prices:
        order_book[order.Price].append(order_book_entry)
    else:
        bisect.insort(order_book_prices, order.Price)
        order_book[order.Price] = [order_book_entry]


def execute_order(order):
    if order.BuySell == 'b':
        quantity_to_fill = order.Quantity
        while quantity_to_fill > 0:
            if SELL_ORDER_BOOK:
                if order.Type == 'm' or SELL_ORDER_PRICES[0] <= order.Price:
                    order_tuple = SELL_ORDER_BOOK[SELL_ORDER_PRICES[0]].pop(0)
                    # order_tuple = (Time, ClientID, Quantity)
                    ordertime, client, qty = order_tuple
                    if qty > quantity_to_fill:
                        # IF Open SELL Limit Order quantity is more than to be filled, update the qty and place it back in order book
                        qty -= quantity_to_fill
                        SELL_ORDER_BOOK[SELL_ORDER_PRICES[0]].insert(0, (ordertime, client, qty))
                        executed_qty, executed_price = quantity_to_fill, SELL_ORDER_PRICES[0]
                        quantity_to_fill = 0
                    else:
                        quantity_to_fill -= qty
                        executed_qty, executed_price = qty, SELL_ORDER_PRICES[0]
                        # Remove entry from SELL Order Book
                        if not SELL_ORDER_BOOK[SELL_ORDER_PRICES[0]]:
                            del SELL_ORDER_BOOK[SELL_ORDER_PRICES[0]]
                            SELL_ORDER_PRICES.pop(0)
                    if order.Type == 'l':
                        EXECUTED_ORDERS.append((order.Time, client, order.ClientID, executed_price, executed_qty))
                    else:
                        EXECUTED_ORDERS.append((order.Time, order.ClientID, client, executed_price, executed_qty))
                else:
                    if order.Type == 'l':
                        # Populate the remaining Limit order
                        order.Quantity = quantity_to_fill
                        add_order_to_book(order)
                    break
            else:
                if order.Type == 'l':
                    order.Quantity = quantity_to_fill
                    add_order_to_book(order)
                break
    elif order.BuySell == 's':
        quantity_to_fill = order.Quantity
        while quantity_to_fill > 0:
            if BUY_ORDER_BOOK:
                if order.Type == 'm' or BUY_ORDER_PRICES[-1] >= order.Price:
                    order_tuple = BUY_ORDER_BOOK[BUY_ORDER_PRICES[-1]].pop(0)
                    # order_tuple = (Time, ClientID, Quantity)
                    ordertime, client, qty = order_tuple
                    if qty > quantity_to_fill:
                        # IF Open BUY Limit Order quantity is more than to be filled, update the qty and place it back in BUY order book
                        qty -= quantity_to_fill
                        BUY_ORDER_BOOK[BUY_ORDER_PRICES[-1]].insert(0, (ordertime, client, qty))
                        executed_qty, executed_price = quantity_to_fill, BUY_ORDER_PRICES[-1]
                        quantity_to_fill = 0
                    else:
                        quantity_to_fill -= qty
                        executed_qty, executed_price = qty, BUY_ORDER_PRICES[-1]
                        if not BUY_ORDER_BOOK[BUY_ORDER_PRICES[-1]]:
                            del BUY_ORDER_BOOK[BUY_ORDER_PRICES[-1]]
                            BUY_ORDER_PRICES.pop()
                    if order.Type == 'l':
                        EXECUTED_ORDERS.append((order.Time, client, order.ClientID, executed_price, executed_qty))
                    else:
                        EXECUTED_ORDERS.append((order.Time, order.ClientID, client, executed_price, executed_qty))

                else:
                    if order.Type == 'l':
                        order.Quantity = quantity_to_fill
                        add_order_to_book(order)
                    break
            else:
                if order.Type == 'l':
                    order.Quantity = quantity_to_fill
                    add_order_to_book(order)
                break
    else:
        logging.warning("Incorrect BuySell flag=%s for order=%s" % (order.BuySell, order))
        raise Exception("Incorrect BuySell flag")


def process_limit_order(order):
    if order.BuySell == 'b':
        if not SELL_ORDER_PRICES or SELL_ORDER_PRICES[0] > order.Price:
            add_order_to_book(order)
        else:
            # Execute Trade
            execute_order(order)
    else:
        # Sell Limit order
        if not BUY_ORDER_PRICES or BUY_ORDER_PRICES[-1] < order.Price:
            add_order_to_book(order)
        else:
            # execute Trade
            execute_order(order)


def _validate_market_order(order):
    if order.BuySell == 'b' and not SELL_ORDER_BOOK:
        # if SELL_ORDER_BOOK is empty, then cancel this trade
        logging.warning("Market BUY Order at %s for ClientID=%s cannot be executed  " \
                        "as SELL_ORDER_BOOK is empty!" % (order.Time, order.ClientID))
        return False
        # TODO: Execute Market BUY Order
    elif order.BuySell == 's' and not BUY_ORDER_BOOK:
        logging.warning("Market SELL Order at %s for ClientID=%s cannot be executed  " \
                        "as BUY_ORDER_BOOK is empty!" % (order.Time, order.ClientID))
        return False
    return True


def process_market_order(order):
    if not _validate_market_order(order):
        return
    execute_order(order)


def process_order(order):
    if order.Type == 'l':
        process_limit_order(order)
    elif order.Type == 'm':
        process_market_order(order)
    else:
        # logging.warning("INVALID Order Type provided. Only 'l' or 'm' values accepted!")
        raise Exception("INVALID Order Type")


def _is_input_valid(order):
    if order.Quantity <= 0:
        return False
    if order.BuySell not in ['b', 's']:
        return False
    if order.Type not in ['m', 'l']:
        return False
    return True


def solve():
    # Write your code here
    order = namedtuple('Order', ['Time', 'ClientID', 'BuySell', 'Quantity', 'Type', 'Price'])
    num_of_orders = int(input())
    for _ in range(num_of_orders):
        order_entry = input().strip().split()
        if len(order_entry) != 6:
            raise Exception("Incorrect Input passed")
        order.Time, order.ClientID, order.BuySell, order.Quantity, order.Type, order.Price = order_entry
        order.Quantity = int(order.Quantity)
        order.Price = round(Decimal(str(order.Price)), 2)
        if _is_input_valid(order):
            process_order(order)

    for executed_order in EXECUTED_ORDERS:
        Time, ClientID1, ClientID2, Price, Quantity = executed_order
        print(Time, ClientID1, ClientID2, str(round(Price, 2)), Quantity)


if __name__ == '__main__':
    solve()