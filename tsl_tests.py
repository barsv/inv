import unittest
from focused_unittest import FocusedTestCase, focus
from tsl import get_trailing_stop_loss_long_profits, trailing_stop_loss_percent
import pandas as pd

class TestExample(FocusedTestCase):

    def test_current_bar_does_not_trigger_sl_but_the_next_does(self):
        """ the 1st bar has low below sl but it shouldn't trigger sl. only on the next bar sl gets triggered."""
        open = 100
        sl_size = open * trailing_stop_loss_percent
        low = open - sl_size
        high = open + sl_size
        close = high - 0.1 * sl_size
        data = {
            'open': [open, close],
            'high': [high, close],
            'low': [low, low],
            'close': [close, low],
        }
        df = pd.DataFrame(data)
        (profits, stop_loss_prices, maximums) = get_trailing_stop_loss_long_profits(df)
        self.assertEqual(len(profits), 2)
        self.assertEqual(len(stop_loss_prices), 2)
        self.assertEqual(len(maximums), 2)
        self.assertEqual(stop_loss_prices[0], high - high * trailing_stop_loss_percent)
        self.assertEqual(maximums[0], high)
        self.assertEqual(profits[0], stop_loss_prices[0] - open)
        self.assertEqual(stop_loss_prices[1], None)
        self.assertEqual(maximums[1], None)
        self.assertEqual(profits[1], None)
    
    def test_current_bar_does_not_trigger_sl_and_no_sl_triggered(self):
        """ the 1st bar has low below sl but it shouldn't trigger sl. 
        and on the next bar sl also doesn't get triggered but it's the last bar."""
        open = 100
        sl_size = open * trailing_stop_loss_percent
        low = open - sl_size
        high = open + sl_size
        close = high - 0.1 * sl_size
        data = {
            'open': [open, close],
            'high': [high, close],
            'low': [low, close],
            'close': [close, close],
        }
        df = pd.DataFrame(data)
        (profits, stop_loss_prices, maximums) = get_trailing_stop_loss_long_profits(df)
        self.assertEqual(len(profits), 2)
        self.assertEqual(len(stop_loss_prices), 2)
        self.assertEqual(len(maximums), 2)
        self.assertEqual(stop_loss_prices[0], None)
        self.assertEqual(maximums[0], None)
        self.assertEqual(profits[0], None)
        self.assertEqual(stop_loss_prices[1], None)
        self.assertEqual(maximums[1], None)
        self.assertEqual(profits[1], None)
    
    def test_3up3down(self):
        """3 bars up, 3 bars down."""
        open = 100
        # move actually should be changing in time but for a small number of bars it's fine to assume it to be constant.
        move = open * trailing_stop_loss_percent / 2
        bit = move * 0.1
        data = {
            'open': [open],
            'low': [open - bit], # low is a bit below open.
            'close': [open + move], # moves up.
            'high': [open + move + bit], # high is a bit above close.
        }
        # next 2 bars go up:
        for i in range(1, 3):
            data['open'].append(data['close'][i - 1]) # opens on the previous close.
            data['low'].append(data['close'][i - 1] - bit) # low is a bit below the open.
            data['close'].append(data['close'][i - 1] + move) # closes a bit below the high.
            data['high'].append(data['close'][i - 1] + move + bit) # high is a bit above the close.
        # next 3 bars go down:
        for i in range(3, 6):
            data['open'].append(data['close'][i - 1]) # opens on the previous close.
            data['high'].append(data['close'][i - 1] + bit) # high is a bit above the open.
            data['close'].append(data['close'][i - 1] - move) # moves down.
            data['low'].append(data['close'][i - 1] - move - bit) # low is a bit below the close.
        data['high'][3] = data['open'][3] + bit / 2 # just to make sure that it is lower than the previous high.
        df = pd.DataFrame(data)
        (profits, stop_loss_prices, maximums) = get_trailing_stop_loss_long_profits(df)
        # there should be 6 bars.
        self.assertEqual(len(profits), 6)
        self.assertEqual(len(stop_loss_prices), 6)
        self.assertEqual(len(maximums), 6)
        # first bar is up
        self.assertEqual(stop_loss_prices[0], data['high'][0] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[0], data['high'][0])
        self.assertEqual(profits[0], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][0])
        # second bar is up
        self.assertEqual(stop_loss_prices[1], data['high'][1] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[1], data['high'][1])
        self.assertEqual(profits[1], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][1])
        # 3rd bar is up
        self.assertEqual(stop_loss_prices[2], data['high'][2] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[2], data['high'][2])
        self.assertEqual(profits[2], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][2])
        # 4th bar is down
        self.assertEqual(maximums[3], data['high'][3])
        self.assertEqual(stop_loss_prices[3], data['high'][3] * (1 - trailing_stop_loss_percent))
        self.assertEqual(profits[3], data['high'][3] * (1 - trailing_stop_loss_percent) - data['open'][3])
        # 5th bar is down
        self.assertEqual(stop_loss_prices[4], data['high'][4] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[4], data['high'][4])
        self.assertEqual(profits[4], data['high'][4] * (1 - trailing_stop_loss_percent) - data['open'][4])
        # 6th bar is down
        self.assertEqual(stop_loss_prices[5], None)
        self.assertEqual(maximums[5], None)
        self.assertEqual(profits[5], None)
        
    def test_3up4down(self):
        """3 bars up, 3 bars down. and one more down but it doesn't trigger sl."""
        open = 100
        # move actually should be changing in time but for a small number of bars it's fine to assume it to be constant.
        move = open * trailing_stop_loss_percent / 2
        bit = move * 0.1
        data = {
            'open': [open],
            'low': [open - bit], # low is a bit below open.
            'close': [open + move], # moves up.
            'high': [open + move + bit], # high is a bit above close.
        }
        # next 2 bars go up:
        for i in range(1, 3):
            data['open'].append(data['close'][i - 1]) # opens on the previous close.
            data['low'].append(data['close'][i - 1] - bit) # low is a bit below the open.
            data['close'].append(data['close'][i - 1] + move) # closes a bit below the high.
            data['high'].append(data['close'][i - 1] + move + bit) # high is a bit above the close.
        # next 3 bars go down:
        for i in range(3, 6):
            data['open'].append(data['close'][i - 1]) # opens on the previous close.
            data['high'].append(data['close'][i - 1] + bit) # high is a bit above the open.
            data['close'].append(data['close'][i - 1] - move) # moves down.
            data['low'].append(data['close'][i - 1] - move - bit) # low is a bit below the close.
        data['high'][3] = data['open'][3] + bit / 2 # just to make sure that it is lower than the previous high.
        # one more bar that doesn't trigger sl for the previous down bar.
        data['open'].append(data['close'][5]) # opens on the previous close.
        data['high'].append(data['close'][5] + bit) # high is a bit above the open.
        data['close'].append(data['close'][5] - bit) # moves down a bit.
        data['low'].append(data['close'][5] - bit) # low is on the close.
        df = pd.DataFrame(data)
        (profits, stop_loss_prices, maximums) = get_trailing_stop_loss_long_profits(df)
        # there should be 6 bars.
        self.assertEqual(len(profits), 7)
        self.assertEqual(len(stop_loss_prices), 7)
        self.assertEqual(len(maximums), 7)
        # first bar is up
        self.assertEqual(stop_loss_prices[0], data['high'][0] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[0], data['high'][0])
        self.assertEqual(profits[0], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][0])
        # second bar is up
        self.assertEqual(stop_loss_prices[1], data['high'][1] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[1], data['high'][1])
        self.assertEqual(profits[1], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][1])
        # 3rd bar is up
        self.assertEqual(stop_loss_prices[2], data['high'][2] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[2], data['high'][2])
        self.assertEqual(profits[2], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][2])
        # 4th bar is down
        self.assertEqual(maximums[3], data['high'][3])
        self.assertEqual(stop_loss_prices[3], data['high'][3] * (1 - trailing_stop_loss_percent))
        self.assertEqual(profits[3], data['high'][3] * (1 - trailing_stop_loss_percent) - data['open'][3])
        # 5th bar is down
        self.assertEqual(stop_loss_prices[4], data['high'][4] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[4], data['high'][4])
        self.assertEqual(profits[4], data['high'][4] * (1 - trailing_stop_loss_percent) - data['open'][4])
        # 6th bar is down
        self.assertEqual(stop_loss_prices[5], None)
        self.assertEqual(maximums[5], None)
        self.assertEqual(profits[5], None)
        # 7th bar is a bit down
        self.assertEqual(stop_loss_prices[5], None)
        self.assertEqual(maximums[5], None)
        self.assertEqual(profits[5], None)

    def test_no_close(self):
        """ 3 bars. SL doesn't get hit at all."""
        open = 100
        sl_size = open * trailing_stop_loss_percent
        high1 = open + sl_size / 3
        high2 = open + sl_size / 2
        low = open - sl_size / 10
        data = {
            'open': [open, open, open],
            'high': [high1, high2, high2],
            'low': [low, low, low],
        }
        df = pd.DataFrame(data)
        (profits, stop_loss_prices, maximums) = get_trailing_stop_loss_long_profits(df)
        self.assertEqual(len(profits), 3)
        self.assertEqual(len(stop_loss_prices), 3)
        self.assertEqual(len(maximums), 3)
        self.assertEqual(stop_loss_prices[0], None)
        self.assertEqual(maximums[0], None)
        self.assertEqual(profits[0], None)
        self.assertEqual(stop_loss_prices[1], None)
        self.assertEqual(maximums[1], None)
        self.assertEqual(profits[1], None)
        self.assertEqual(stop_loss_prices[2], None)
        self.assertEqual(maximums[2], None)
        self.assertEqual(profits[2], None)

    @focus
    def test_3up3down_3up2down(self):
        """3 bars up, 3 bars down. the last down bar triggers sl. then the situation is repeated."""
        open = 100
        # move actually should be changing in time but for a small number of bars it's fine to assume it to be constant.
        move = open * trailing_stop_loss_percent / 2
        bit = move * 0.1
        # bar 0 goes up.
        data = {
            'open': [open],
            'high': [open + move + bit], # high is a bit above close.
            'low': [open - bit], # low is a bit below open.
            'close': [open + move], # moves up.
        }
        # bars 1,2 go up:
        for i in range(1, 3):
            data['open'].append(data['close'][i - 1]) # opens on the previous close.
            data['high'].append(data['close'][i - 1] + move + bit) # high is a bit above the close.
            data['low'].append(data['close'][i - 1] - bit) # low is a bit below the open.
            data['close'].append(data['close'][i - 1] + move) # closes a bit below the high.
        # bar 2 has big high but closes just a bit above open so that bar 5 doesn't trigger sl for bar 3.
        data['close'][2] = data['close'][i - 1] + bit # closes a bit below the high.
        # bar 3 goes down a bit and doesn't trigger sl.
        data['open'].append(data['close'][2]) # opens on the previous close.
        data['high'].append(data['close'][2] + bit / 2) # /2 to make sure that it is lower than the previous high.
        data['close'].append(data['close'][2] - bit) # moves down a bit.
        data['low'].append(data['close'][2] - bit - bit / 2) # low is a bit below the close.
        # bar 4 goes down just a bit. it doesn't trigger sl yet.
        data['open'].append(data['close'][3]) # opens on the previous close.
        data['high'].append(data['close'][3] + bit) # high is a bit above the open.
        data['close'].append(data['close'][3] - bit) # moves down a bit.
        data['low'].append(data['close'][3] - bit - bit / 2) # low is a bit below the close.
        # bar 5 also goes down and triggers sl for the up bars but not for bars 3,4.
        data['open'].append(data['close'][4]) # opens on the previous close.
        data['high'].append(data['close'][4] + bit / 2) # high is a bit above the open.
        data['low'].append(data['close'][4] - move - bit) # low is a bit below the close.
        data['close'].append(data['close'][4] - move) # moves down.
        # next 3 bars go up.
        for i in range(6, 9):
            data['open'].append(data['close'][i - 1]) # opens on the previous close.
            data['high'].append(data['close'][i - 1] + move + bit) # high is a bit above the close.
            data['low'].append(data['close'][i - 1] - bit) # low is a bit below the open.
            data['close'].append(data['close'][i - 1] + move) # closes a bit below the high.
        # next 2 bars go down:
        for i in range(9, 11):
            data['open'].append(data['close'][i - 1]) # opens on the previous close.
            data['high'].append(data['close'][i - 1] + bit) # high is a bit above the open.
            data['close'].append(data['close'][i - 1] - move) # moves down.
            data['low'].append(data['close'][i - 1] - move - bit) # low is a bit below the close.
        data['high'][9] = data['open'][9] + bit / 2 # just to make sure that it is lower than the previous high.
        df = pd.DataFrame(data)
        (profits, stop_loss_prices, maximums) = get_trailing_stop_loss_long_profits(df)
        # there should be 11 bars.
        self.assertEqual(len(profits), 11)
        self.assertEqual(len(stop_loss_prices), 11)
        self.assertEqual(len(maximums), 11)
        # bar 0 goes up
        self.assertEqual(stop_loss_prices[0], data['high'][0] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[0], data['high'][0])
        self.assertEqual(profits[0], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][0])
        # bar 1 goes up
        self.assertEqual(stop_loss_prices[1], data['high'][1] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[1], data['high'][1])
        self.assertEqual(profits[1], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][1])
        # bar 2 goes up
        self.assertEqual(stop_loss_prices[2], data['high'][2] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[2], data['high'][2])
        self.assertEqual(profits[2], data['high'][2] * (1 - trailing_stop_loss_percent) - data['open'][2])
        # bar 3 goes down
        self.assertEqual(maximums[3], data['high'][3])
        self.assertEqual(stop_loss_prices[3], data['high'][3] * (1 - trailing_stop_loss_percent))
        self.assertEqual(profits[3], data['high'][3] * (1 - trailing_stop_loss_percent) - data['open'][3])
        # bar 4 goes down just a bit. bar 5 will not trigger sl for bar 4. sl will be triggered on bar 8.
        self.assertEqual(stop_loss_prices[4], data['high'][4] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[4], data['high'][4])
        self.assertEqual(profits[4], data['high'][8] * (1 - trailing_stop_loss_percent) - data['open'][4])
        # bar 5 goes down. max and sl are the same as for bar 4. sl will be triggered on bar 8.
        self.assertEqual(stop_loss_prices[5], data['high'][4] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[5], data['high'][4])
        self.assertEqual(profits[5], data['high'][8] * (1 - trailing_stop_loss_percent) - data['open'][5])
        # bar 6 goes up but doesn't reach high of bar 4. sl will be triggered on bar 8.
        self.assertEqual(stop_loss_prices[6], data['high'][4] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[6], data['high'][4])
        self.assertEqual(profits[6], data['high'][8] * (1 - trailing_stop_loss_percent) - data['open'][6])
        # bar 7 goes up above previous max high.
        self.assertEqual(stop_loss_prices[7], data['high'][7] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[7], data['high'][7])
        self.assertEqual(profits[7], data['high'][8] * (1 - trailing_stop_loss_percent) - data['open'][7])
        # bar 8 goes up above previous max high.
        self.assertEqual(stop_loss_prices[8], data['high'][8] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[8], data['high'][8])
        self.assertEqual(profits[8], data['high'][8] * (1 - trailing_stop_loss_percent) - data['open'][8])
        # bar 9 goes down but doesn't trigger sl.
        self.assertEqual(stop_loss_prices[9], data['high'][9] * (1 - trailing_stop_loss_percent))
        self.assertEqual(maximums[9], data['high'][9])
        self.assertEqual(profits[9], data['high'][9] * (1 - trailing_stop_loss_percent) - data['open'][9])
        # bar 10 goes down and it's the last bar.
        self.assertEqual(stop_loss_prices[10], None)
        self.assertEqual(maximums[10], None)
        self.assertEqual(profits[10], None)

if __name__ == '__main__':
    unittest.main()
