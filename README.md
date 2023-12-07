# CHC1203-canbus
Code and documentation about Quick's CHC1203 chain counter. 

## Canbus settings
The CHC1203 has a built-in canbus 120Ohm terminator. So it needs to be at the start or end of bus. The canbus network speed is 62000Kbps.

## Protocol

When the CHC1203 boots up alone on the network, it immediatly starts broadcasting its state. With my unit I get:

```
can0  6C0   [8]  C1 18 78 00 01 00 01 00 
can0  6C1   [8]  C1 18 6B 00 00 00 02 00 
can0  6C2   [8]  C1 18 00 00 00 00 00 00 
can0  6C3   [8]  C1 18 00 00 00 00 00 00 
```

## Master-Slave

If I connect a slave unit such as a CHC1102M I get some traffic. I think it ensures there is only one master on the canbus, but also any settings changed on the slave get propagated to the master.

