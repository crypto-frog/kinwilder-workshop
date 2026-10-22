#!/usr/bin/env python3
import random, sys
rng=random.Random(int(sys.argv[1]) if len(sys.argv)>1 else 7)
trees=sorted(rng.sample(range(2,27),5))
for glyph in ("^","A","|"):
    print("".join(glyph if x in trees else " " for x in range(30)))
