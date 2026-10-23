#!/usr/bin/env python3
"""Hadoop Streaming MAPPER – emits key = station|year-month, value = metrics.
Missing/invalid fields are skipped gracefully (counted, not fatal).
Columns follow data/sample_dataset.csv (without header)."""
import sys
for line in sys.stdin:
    f = line.rstrip("\n").split(",")
    if len(f) < 24 or f[0] == "record_id":
        sys.stderr.write("reporter:counter:EarthScape,BadRecords,1\n"); continue
    station, date = f[1], f[8]
    def num(i):
        try: return float(f[i])
        except ValueError: sys.stderr.write("reporter:counter:EarthScape,MissingValues,1\n"); return None
    t, rain, wind, pm = num(9), num(13), num(14), num(17)
    vals = [("" if v is None else str(v)) for v in (t, rain, wind, pm)]
    print(f"{station}|{date[:7]}\t{','.join(vals)},{f[22]}")
