from skidl import *

# 1. Define Nets (Nodes)
v_batt = Net('V_BATT')
gnd    = Net('0')
soc    = Net('SOC')

# 2. Instantiate Components
battery = Part('components/lifepo4_50ah.lib', 'LiFePO4_50Ah')
load    = Part('Device', 'I', value='50A')

# 3. Wire Components Together
battery['POS', 'NEG', 'SOC_OUT'] += v_batt, gnd, soc
load['1', '2']                   += v_batt, gnd

# 4. Generate SPICE Netlist
generate_netlist(outfile='generated_circuit.net')