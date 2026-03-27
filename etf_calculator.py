#!/usr/bin/env python3
"""
ETF Trading Frenzy Calculator — WQC Spring 2026
=================================================
Track estimated bot positions for E, T, F and compute settlements + ETF fair value.
Update one value at a time without re-entering everything.

Settlement(X) = 500 + (NB(X) + EB(X)) / 100
ETF = (E + 2T + 3F) / 6
"""

class ETFCalculator:
    def __init__(self):
        # Estimated net positions of noise bots and event bots
        self.noise_bot = {'E': 0.0, 'T': 0.0, 'F': 0.0}
        self.event_bot = {'E': 0.0, 'T': 0.0, 'F': 0.0}

    def settlement(self, sym):
        return 500 + (self.noise_bot[sym] + self.event_bot[sym]) / 100

    def etf_settlement(self):
        e, t, f = self.settlement('E'), self.settlement('T'), self.settlement('F')
        return (e + 2 * t + 3 * f) / 6

    def display(self):
        e_s = self.settlement('E')
        t_s = self.settlement('T')
        f_s = self.settlement('F')
        etf_s = self.etf_settlement()

        print("\n" + "=" * 62)
        print("  ETF Trading Frenzy — Fair Values")
        print("=" * 62)
        print(f"  {'Symbol':<6} {'NB Pos':>8} {'EB Pos':>8} {'Total Pos':>10} {'Settlement':>11}")
        print("  " + "-" * 56)
        for sym in ['E', 'T', 'F']:
            nb = self.noise_bot[sym]
            eb = self.event_bot[sym]
            total = nb + eb
            s = self.settlement(sym)
            print(f"  {sym:<6} {nb:>8.0f} {eb:>8.0f} {total:>10.0f} {s:>11.2f}")

        print()
        print(f"  ETF = (E + 2T + 3F) / 6")
        print(f"      = ({e_s:.2f} + 2×{t_s:.2f} + 3×{f_s:.2f}) / 6")
        print(f"      = ({e_s:.2f} + {2*t_s:.2f} + {3*f_s:.2f}) / 6")
        print(f"      = {e_s + 2*t_s + 3*f_s:.2f} / 6")
        print(f"      = {etf_s:.2f}")

        print()
        print(f"  Component weights in ETF:")
        print(f"    E  contributes {e_s/6:.2f}  ({e_s/(e_s+2*t_s+3*f_s)*100:.1f}% of numerator)")
        print(f"    2T contributes {2*t_s/6:.2f}  ({2*t_s/(e_s+2*t_s+3*f_s)*100:.1f}% of numerator)")
        print(f"    3F contributes {3*f_s/6:.2f}  ({3*f_s/(e_s+2*t_s+3*f_s)*100:.1f}% of numerator)")

        # Arb check: if someone gives you a market ETF price
        print()
        print(f"  Synthetic ETF (from singles) = {etf_s:.2f}")
        print("=" * 62)


def print_help():
    print("""
  Commands (case-insensitive):
  ─────────────────────────────────────────────────────
  nb E 500      Set noise bot position for E to 500
  eb T -300     Set event bot position for T to -300
  nb F +200     Add 200 to noise bot position for F
  eb E +150     Add 150 to event bot position for E

  arb <price>   Check ETF arb: compare market price to synthetic
  reset         Reset everything to 0
  help          Show this help
  q             Quit
  ─────────────────────────────────────────────────────
  Tip: prefix a number with + or - to ADD to current value
       instead of replacing it. e.g. "nb E +100"
""")


def main():
    calc = ETFCalculator()

    print("╔══════════════════════════════════════════════╗")
    print("║   ETF Trading Frenzy Calculator              ║")
    print("║   WQC Spring 2026                            ║")
    print("╚══════════════════════════════════════════════╝")
    print_help()
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

            elif cmd == 'reset':
                calc.noise_bot = {'E': 0.0, 'T': 0.0, 'F': 0.0}
                calc.event_bot = {'E': 0.0, 'T': 0.0, 'F': 0.0}
                print("  Reset all positions to 0.")
                calc.display()

            elif cmd == 'arb' and len(parts) == 2:
                market_etf = float(parts[1])
                synthetic = calc.etf_settlement()
                diff = market_etf - synthetic
                print(f"\n  Market ETF:    {market_etf:.2f}")
                print(f"  Synthetic ETF: {synthetic:.2f}")
                print(f"  Difference:    {diff:+.2f}")
                if abs(diff) < 0.5:
                    print(f"  → No significant arb.")
                elif diff > 0:
                    print(f"  → ETF is RICH. Sell ETF, buy singles.")
                else:
                    print(f"  → ETF is CHEAP. Buy ETF, sell singles.")

            elif cmd in ('nb', 'eb') and len(parts) == 3:
                sym = parts[1].upper()
                val_str = parts[2]

                if sym not in ('E', 'T', 'F'):
                    print("  Symbol must be E, T, or F")
                    continue

                target = calc.noise_bot if cmd == 'nb' else calc.event_bot

                # Check if it's an increment (+/-) or an absolute set
                if val_str.startswith('+') or (val_str.startswith('-') and val_str != '-'):
                    delta = float(val_str)
                    old = target[sym]
                    target[sym] += delta
                    label = "Noise Bot" if cmd == 'nb' else "Event Bot"
                    print(f"  {label} {sym}: {old:.0f} → {target[sym]:.0f} ({val_str})")
                else:
                    target[sym] = float(val_str)

                calc.display()

            else:
                print("  Unknown command. Type 'help' for usage.")

        except ValueError:
            print("  Invalid number. Try again.")
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break


if __name__ == '__main__':
    main()
