# Attribution — Zephyr tick conversion

- Zephyr RTOS tag **v3.6.0**, peeled commit `468eb56cf242eedba62006ee758700ee6148763f`
  https://github.com/zephyrproject-rtos/zephyr

**What we kept.** Integer conversion of a microsecond tick into a millisecond epoch by dividing by about 1000.

**What we changed.** Isolated one function. No sensor bus, no `k_uptime_get`. Relative error vs `/1000` is an explicit `Post` (2.5%), with `Pre` `tick >= 640000` because integer `/1024` overshoots that bound near 600000. That floor is a stated assumption, not a CBMC default.
