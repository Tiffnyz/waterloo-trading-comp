#!/usr/bin/env python3
"""
Octomarket Calculator — WQC Spring 2026
=========================================
Track d20 rolls for Teams A and B, compute fair values for all 8 contracts.

Contracts:
  WIN A / WIN B       — whose sum is higher
  ODD A / ODD B       — who has more odd rolls
  DIV A / DIV B       — whose product has more divisors
  SPREAD S            — |sum diff| > 5.5
  SPREAD L            — |sum diff| > 20.5
"""

import math
import random

# ─── Prime factorization lookup for 1-20 ─────────────────────────

PRIME_FACTORS = {
    1:  {},
    2:  {2: 1},
    3:  {3: 1},
    4:  {2: 2},
    5:  {5: 1},
    6:  {2: 1, 3: 1},
    7:  {7: 1},
    8:  {2: 3},
    9:  {3: 2},
    10: {2: 1, 5: 1},
    11: {11: 1},
    12: {2: 2, 3: 1},
    13: {13: 1},
    14: {2: 1, 7: 1},
    15: {3: 1, 5: 1},
    16: {2: 4},
    17: {17: 1},
    18: {2: 1, 3: 2},
    19: {19: 1},
    20: {2: 2, 5: 1},
}

PRIME_STRINGS = {
    1:  "1",
    2:  "2",
    3:  "3",
    4:  "2²",
    5:  "5",
    6:  "2 × 3",
    7:  "7",
    8:  "2³",
    9:  "3²",
    10: "2 × 5",
    11: "11",
    12: "2² × 3",
    13: "13",
    14: "2 × 7",
    15: "3 × 5",
    16: "2⁴",
    17: "17",
    18: "2 × 3²",
    19: "19",
    20: "2² × 5",
}


def merge_exponents(d1, d2):
    """Combine two prime exponent dictionaries."""
    result = dict(d1)
    for p, e in d2.items():
        result[p] = result.get(p, 0) + e
    return result


def count_divisors(exp_dict):
    """τ(n) = Π(eᵢ + 1)"""
    if not exp_dict:
        return 1
    result = 1
    for e in exp_dict.values():
        result *= (e + 1)
    return result


def norm_cdf(x):
    """Standard normal CDF via error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ─── Calculator ───────────────────────────────────────────────────

class OctomarketCalculator:
    def __init__(self):
        self.rolls_a = []
        self.rolls_b = []
        self.num_sims = 30000  # Monte Carlo simulations for DIV

    # ── Helpers ────────────────────────────────────────────────────

    def remaining_a(self):
        return 10 - len(self.rolls_a)

    def remaining_b(self):
        return 10 - len(self.rolls_b)

    def sum_a(self):
        return sum(self.rolls_a)

    def sum_b(self):
        return sum(self.rolls_b)

    def odd_count(self, rolls):
        return sum(1 for r in rolls if r % 2 == 1)

    def exponents(self, rolls):
        result = {}
        for r in rolls:
            result = merge_exponents(result, PRIME_FACTORS[r])
        return result

    # ── WIN contracts (normal approx) ─────────────────────────────

    def price_win(self):
        sa, sb = self.sum_a(), self.sum_b()
        ra, rb = self.remaining_a(), self.remaining_b()

        if ra == 0 and rb == 0:
            if sa > sb:   return 100.0, 0.0
            elif sa < sb: return 0.0, 100.0
            else:         return 50.0, 50.0

        # Difference distribution: SA_final - SB_final
        mean_diff = (sa - sb) + 10.5 * (ra - rb)
        var_diff = 33.25 * (ra + rb)
        sd_diff = math.sqrt(var_diff) if var_diff > 0 else 0.001

        p_a_wins = 1.0 - norm_cdf(-mean_diff / sd_diff)
        # Small discrete-tie correction
        p_tie = math.exp(-mean_diff ** 2 / (2 * var_diff)) / (sd_diff * math.sqrt(2 * math.pi))
        p_tie = min(p_tie, 0.1)  # cap at reasonable level

        win_a = 100 * (p_a_wins - p_tie / 2) + 50 * p_tie
        win_b = 100 * (1 - p_a_wins - p_tie / 2) + 50 * p_tie
        return max(0, min(100, win_a)), max(0, min(100, win_b))

    # ── SPREAD contracts (normal approx) ──────────────────────────

    def price_spread(self):
        sa, sb = self.sum_a(), self.sum_b()
        ra, rb = self.remaining_a(), self.remaining_b()

        if ra == 0 and rb == 0:
            diff = abs(sa - sb)
            return (100.0 if diff > 5.5 else 0.0), (100.0 if diff > 20.5 else 0.0)

        mean_diff = (sa - sb) + 10.5 * (ra - rb)
        var_diff = 33.25 * (ra + rb)
        sd = math.sqrt(var_diff) if var_diff > 0 else 0.001

        def p_abs_gt(threshold):
            return (1 - norm_cdf((threshold - mean_diff) / sd)
                    + norm_cdf((-threshold - mean_diff) / sd))

        p_s = p_abs_gt(5.5)
        p_l = p_abs_gt(20.5)
        return max(0, min(100, 100 * p_s)), max(0, min(100, 100 * p_l))

    # ── ODD contracts (exact binomial) ────────────────────────────

    def price_odd(self):
        oa = self.odd_count(self.rolls_a)
        ob = self.odd_count(self.rolls_b)
        ra = self.remaining_a()
        rb = self.remaining_b()

        def binom_pmf(n, k):
            if k < 0 or k > n:
                return 0.0
            return math.comb(n, k) * (0.5 ** n)

        p_a_wins = 0.0
        p_tie = 0.0
        for da in range(ra + 1):
            pa = binom_pmf(ra, da)
            for db in range(rb + 1):
                pb = binom_pmf(rb, db)
                total_a = oa + da
                total_b = ob + db
                prob = pa * pb
                if total_a > total_b:
                    p_a_wins += prob
                elif total_a == total_b:
                    p_tie += prob

        odd_a = 100 * p_a_wins + 50 * p_tie
        odd_b = 100 * (1 - p_a_wins - p_tie) + 50 * p_tie
        return max(0, min(100, odd_a)), max(0, min(100, odd_b))

    # So the workflow each minute is:
    # New rolls drop → type ab 14 7 (or whatever they are)
    # Glance at all 8 contract fair values
    # Compare to what's being quoted on the exchange
    # If any contract is 5+ away from your fair value → trade it
    # If nothing is mispriced → do nothing and wait for the next roll


    # ── DIV contracts (Monte Carlo) ───────────────────────────────

    # If the market price is below your fair value, buy. 
    # If it's above your fair value, sell. 
    # The bigger the gap, the more confident you should be.

    # Rolls 6–10 are where DIV trading gets really profitable because by then 
    # you can see most of the prime factorization building up and 
    # other teams might not be computing it correctly.

    # If offering DIV A at 42 and fair value is 53 → you buy from the bot (lift the offer). 
    # If bidding DIV B at 60 and fair value is 53 → you sell to the bot (hit the bid). You just sold something worth 53 for 60.
    
    def price_div(self):
        ea = self.exponents(self.rolls_a)
        eb = self.exponents(self.rolls_b)
        ra = self.remaining_a()
        rb = self.remaining_b()

        if ra == 0 and rb == 0:
            da = count_divisors(ea)
            db = count_divisors(eb)
            if da > db:   return 100.0, 0.0
            elif da < db: return 0.0, 100.0
            else:         return 50.0, 50.0

        a_wins = 0
        ties = 0

        for _ in range(self.num_sims):
            sim_a = dict(ea)
            for __ in range(ra):
                r = random.randint(1, 20)
                for p, e in PRIME_FACTORS[r].items():
                    sim_a[p] = sim_a.get(p, 0) + e

            sim_b = dict(eb)
            for __ in range(rb):
                r = random.randint(1, 20)
                for p, e in PRIME_FACTORS[r].items():
                    sim_b[p] = sim_b.get(p, 0) + e

            da = count_divisors(sim_a)
            db = count_divisors(sim_b)
            if da > db:
                a_wins += 1
            elif da == db:
                ties += 1

        n = self.num_sims
        p_a = a_wins / n
        p_tie = ties / n
        div_a = 100 * p_a + 50 * p_tie
        div_b = 100 * (1 - p_a - p_tie) + 50 * p_tie
        return max(0, min(100, div_a)), max(0, min(100, div_b))

    # ── Display ───────────────────────────────────────────────────

    def display(self):
        sa, sb = self.sum_a(), self.sum_b()
        ra, rb = self.remaining_a(), self.remaining_b()
        oa, ob = self.odd_count(self.rolls_a), self.odd_count(self.rolls_b)
        ea, eb = self.exponents(self.rolls_a), self.exponents(self.rolls_b)
        da_so_far, db_so_far = count_divisors(ea), count_divisors(eb)

        rolls_a_str = ', '.join(str(r) for r in self.rolls_a) if self.rolls_a else '—'
        rolls_b_str = ', '.join(str(r) for r in self.rolls_b) if self.rolls_b else '—'

        print("\n" + "=" * 62)
        print("  Octomarket — Contract Fair Values")
        print("=" * 62)

        print(f"  Team A rolls ({len(self.rolls_a):>2}/10): {rolls_a_str}")
        print(f"    Sum = {sa}   Odd count = {oa}   Divisors (so far) = {da_so_far}")
        print(f"  Team B rolls ({len(self.rolls_b):>2}/10): {rolls_b_str}")
        print(f"    Sum = {sb}   Odd count = {ob}   Divisors (so far) = {db_so_far}")

        print(f"\n  Expected remaining sums: A +{10.5*ra:.1f}  B +{10.5*rb:.1f}")
        print(f"  Expected final sums:     A ≈{sa + 10.5*ra:.1f}  B ≈{sb + 10.5*rb:.1f}")

        print(f"\n  ┌────────────┬────────┬────────┐")
        print(f"  │ Contract   │  Fair$ │  Comp  │")
        print(f"  ├────────────┼────────┼────────┤")

        win_a, win_b = self.price_win()
        print(f"  │ WIN A      │ {win_a:5.1f}  │        │")
        print(f"  │ WIN B      │ {win_b:5.1f}  │ {win_a+win_b:5.1f}  │")
        print(f"  ├────────────┼────────┼────────┤")

        odd_a, odd_b = self.price_odd()
        print(f"  │ ODD A      │ {odd_a:5.1f}  │        │")
        print(f"  │ ODD B      │ {odd_b:5.1f}  │ {odd_a+odd_b:5.1f}  │")
        print(f"  ├────────────┼────────┼────────┤")

        print(f"  │ DIV A      │  ...   │  MC    │")
        print(f"  │ DIV B      │  ...   │  sim   │")

        spread_s, spread_l = self.price_spread()
        print(f"  ├────────────┼────────┼────────┤")
        print(f"  │ SPREAD S   │ {spread_s:5.1f}  │ >5.5   │")
        print(f"  │ SPREAD L   │ {spread_l:5.1f}  │ >20.5  │")
        print(f"  └────────────┴────────┴────────┘")

        # DIV takes a moment — run separately
        print(f"  Computing DIV via Monte Carlo ({self.num_sims} sims)...")
        div_a, div_b = self.price_div()
        print(f"  ┌────────────┬────────┐")
        print(f"  │ DIV A      │ {div_a:5.1f}  │")
        print(f"  │ DIV B      │ {div_b:5.1f}  │")
        print(f"  └────────────┴────────┘")

        # Sanity checks
        print(f"\n  Pair sums: WIN={win_a+win_b:.1f}  ODD={odd_a+odd_b:.1f}  DIV={div_a+div_b:.1f}  (should ≈100)")
        print("=" * 62)

    def display_lookup(self):
        print("\n  ┌──────┬─────────────┬──────────────────────────┐")
        print("  │ Roll │ Factorizatn │ Primes hit               │")
        print("  ├──────┼─────────────┼──────────────────────────┤")
        for i in range(1, 21):
            ps = PRIME_STRINGS[i]
            primes = sorted(PRIME_FACTORS[i].keys()) if PRIME_FACTORS[i] else ['-']
            primes_str = ', '.join(str(p) for p in primes)
            print(f"  │  {i:>2}  │ {ps:<11} │ {primes_str:<24} │")
        print("  └──────┴─────────────┴──────────────────────────┘")

    def display_exponent_table(self):
        """Show current prime exponent vectors for both teams."""
        ea = self.exponents(self.rolls_a)
        eb = self.exponents(self.rolls_b)
        all_primes = sorted(set(list(ea.keys()) + list(eb.keys())))

        if not all_primes:
            print("  No rolls yet — no exponents to show.")
            return

        print(f"\n  Prime exponent vectors:")
        print(f"  {'Prime':<8}", end="")
        for p in all_primes:
            print(f"  {p:>3}", end="")
        print(f"  │  τ(product)")
        print(f"  {'─'*8}", end="")
        for _ in all_primes:
            print(f"  {'─'*3}", end="")
        print(f"  │  {'─'*11}")
        for label, exps in [("Team A", ea), ("Team B", eb)]:
            print(f"  {label:<8}", end="")
            for p in all_primes:
                print(f"  {exps.get(p,0):>3}", end="")
            print(f"  │  {count_divisors(exps)}")
        print()


def print_help():
    print("""
  Commands:
  ─────────────────────────────────────────────────
  a <roll>        Add a roll for Team A (1-20)
  b <roll>        Add a roll for Team B (1-20)
  ab <rA> <rB>    Add both rolls at once (saves time)
  undo a          Remove last Team A roll
  undo b          Remove last Team B roll
  lookup          Show prime factorization table (1-20)
  exponents       Show prime exponent vectors
  sims <n>        Set number of Monte Carlo sims (default 30000)
  reset           Clear all rolls
  help            Show this help
  q               Quit
  ─────────────────────────────────────────────────
  Rolls are revealed in pairs each minute, so 'ab 14 7'
  is the fastest way to enter them.
""")


def main():
    calc = OctomarketCalculator()

    print("╔══════════════════════════════════════════════╗")
    print("║   Octomarket Calculator                      ║")
    print("║   WQC Spring 2026                            ║")
    print("╚══════════════════════════════════════════════╝")
    print_help()
    calc.display_lookup()
    calc.display()

    while True:
        try:
            raw = input("\n> ").strip()
            if not raw:
                continue
            parts = raw.split()
            cmd = parts[0].lower()

            if cmd in ('q', 'quit', 'exit'):
                print("  Goodbye!")
                break

            elif cmd == 'help':
                print_help()
                continue

            elif cmd == 'lookup':
                calc.display_lookup()
                continue

            elif cmd == 'exponents':
                calc.display_exponent_table()
                continue

            elif cmd == 'reset':
                calc.rolls_a = []
                calc.rolls_b = []
                print("  All rolls cleared.")
                calc.display()

            elif cmd == 'sims' and len(parts) == 2:
                calc.num_sims = max(1000, int(parts[1]))
                print(f"  Monte Carlo sims set to {calc.num_sims}")
                continue

            elif cmd == 'undo' and len(parts) == 2:
                team = parts[1].lower()
                if team == 'a' and calc.rolls_a:
                    removed = calc.rolls_a.pop()
                    print(f"  Removed {removed} from Team A")
                    calc.display()
                elif team == 'b' and calc.rolls_b:
                    removed = calc.rolls_b.pop()
                    print(f"  Removed {removed} from Team B")
                    calc.display()
                else:
                    print("  Nothing to undo.")

            elif cmd == 'ab' and len(parts) == 3:
                ra = int(parts[1])
                rb = int(parts[2])
                if not (1 <= ra <= 20) or not (1 <= rb <= 20):
                    print("  Rolls must be 1-20")
                    continue
                if len(calc.rolls_a) >= 10 or len(calc.rolls_b) >= 10:
                    print("  A team already has 10 rolls")
                    continue
                calc.rolls_a.append(ra)
                calc.rolls_b.append(rb)
                print(f"  Added A={ra}, B={rb}")
                calc.display()

            elif cmd == 'a' and len(parts) == 2:
                roll = int(parts[1])
                if 1 <= roll <= 20 and len(calc.rolls_a) < 10:
                    calc.rolls_a.append(roll)
                    print(f"  Added {roll} to Team A")
                    calc.display()
                else:
                    print("  Invalid (1-20, max 10 rolls)")

            elif cmd == 'b' and len(parts) == 2:
                roll = int(parts[1])
                if 1 <= roll <= 20 and len(calc.rolls_b) < 10:
                    calc.rolls_b.append(roll)
                    print(f"  Added {roll} to Team B")
                    calc.display()
                else:
                    print("  Invalid (1-20, max 10 rolls)")

            else:
                print("  Unknown command. Type 'help' for usage.")

        except ValueError:
            print("  Invalid number. Try again.")
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break


if __name__ == '__main__':
    main()
