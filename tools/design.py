"""UTS Mini Mixing Desk, Compressor module - authoritative netlist.
Each entry: (ref, lib, symname, value, footprint, block, {pin: net})
Op-amp packages appear as three units: A (unit1), B (unit2), P (unit3 = power pins).
"""
FP_R   = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
FP_CC  = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
FP_CF  = 'Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm'
# Real film parts (element14, Oct 2026): TDK B32562H1106K000 10u, B32562H1475K000 4u7, KEMET MMK5225K63J06L4BULK 2u2
FP_F10 = 'Capacitor_THT:C_Rect_L16.5mm_W11.8mm_P15.00mm_MKT'
FP_F47 = 'Capacitor_THT:C_Rect_L16.5mm_W7.3mm_P15.00mm_MKT'
FP_F22 = 'Capacitor_THT:C_Rect_L7.2mm_W7.2mm_P5.00mm_FKS2_FKP2_MKS2_MKP2'
FP_CE  = 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm'
FP_D   = 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal'
FP_D4  = 'Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal'
FP_LED = 'LED_THT:LED_D3.0mm'
FP_Q   = 'Package_TO_SOT_THT:TO-92_Inline'
FP_OA  = 'Package_DIP:DIP-8_W7.62mm'
FP_POT = 'Potentiometer_THT:Potentiometer_Alps_RK09K_Single_Vertical'
FP_TRM = 'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical'

def R(ref,val,a,b,blk,fp=FP_R):   return (ref,'Device','R',val,fp,blk,{'1':a,'2':b})
def C(ref,val,a,b,blk,fp=FP_CC):  return (ref,'Device','C',val,fp,blk,{'1':a,'2':b})
def CP(ref,val,p,m,blk):          return (ref,'Device','C_Polarized',val,FP_CE,blk,{'1':p,'2':m})
def D(ref,val,anode,cath,blk,fp=FP_D): return (ref,'Device','D',val,fp,blk,{'2':anode,'1':cath})
def Z(ref,val,anode,cath,blk):    return (ref,'Device','D_Zener',val,FP_D,blk,{'2':anode,'1':cath})
def Q(ref,c,b,e,blk):             return (ref,'Transistor_BJT','BC549','BC549C',FP_Q,blk,{'1':c,'2':b,'3':e})
def POT(ref,val,p1,w,p3,blk,fp=FP_POT): return (ref,'Device','R_Potentiometer',val,fp,blk,{'1':p1,'2':w,'3':p3})

def OA(ref,unit,pins,blk):
    return (ref,'Amplifier_Operational','NE5532','NE5532',FP_OA,blk,pins,unit)

PARTS = []
A=PARTS.append

# ---------------- J1 : 500-series card edge ----------------
A(('J1','Connector_Generic','Conn_01x15','500 card edge','',
   'CONNECTOR',{'1':'CHASSIS','2':'OUT+','3':'AUXOUT+','4':'OUT-','5':'AGND','6':'LINK',
                '7':'AUXOUT-','8':'IN-','9':'AUXIN-','10':'IN+','11':'AUXIN+',
                '12':'+16V-IN','13':'PGND','14':'-16V-IN','15':'P48-NC'}))

# ---------------- Sheet 1 : input receiver + pad ----------------
B1='SH1 INPUT RECEIVER AND PAD'
A(R('R5','100R','IN-','N1',B1));      A(C('C3','1n','N1','AGND',B1))
A(C('C1','22u','N1','N2',B1,FP_CE));  A(R('R2','22k','N2','INV1',B1))
A(R('R6','100R','IN+','N3',B1));      A(C('C4','1n','N3','AGND',B1))
A(C('C2','22u','N3','N4',B1,FP_CE));  A(R('R1','22k','N4','NINV1',B1))
A(R('R3','22k','NINV1','AGND',B1));   A(R('R4','22k','INV1','SIG-IN',B1))
A(OA('U1',1,{'3':'NINV1','2':'INV1','1':'SIG-IN'},B1))
A(R('R7','8k2','SIG-IN','PADX',B1))
A(POT('RV1','2k','PADX','PAD','PAD',B1,FP_TRM))
A(R('R8','75R','PAD','AGND',B1))

# ---------------- Sheet 2 : steering VCA + recovery ----------------
B2='SH2 STEERING VCA AND RECOVERY AMP'
A(C('C5','10u','PAD','Q1B',B2,FP_F10)); A(R('R11','10k','Q1B','VBIAS',B2))
A(Q('Q1','EA','Q1B','Q1E',B2));        A(R('R14','220R','Q1E','TAIL',B2))
A(Q('Q2','EB','Q2B','Q2E',B2));        A(R('R15','220R','Q2E','TAIL',B2))
A(R('R12','10k','Q2B','VBIAS',B2));    A(R('R13','220R','Q2B','C8A',B2))
A(C('C8','10u','C8A','AGND',B2,FP_F10))
A(Q('Q3','TAIL','AGND','Q3E',B2));     A(R('R18','1k5','Q3E','-5V1',B2))
A(Q('Q6','+16V','STA','EA',B2));       A(Q('Q7','CP','STB','EA',B2))
A(Q('Q8','+16V','STA','EB',B2));       A(Q('Q9','CN','STB','EB',B2))
A(R('R16','4k7','+16V','CP',B2));      A(R('R17','4k7','+16V','CN',B2))
A(Q('Q4','+16V','CP','E1',B2));        A(Q('Q5','+16V','CN','E2',B2))
A(R('R19','10k','E1','AGND',B2));      A(R('R20','10k','E2','AGND',B2))
A(C('C9','4u7','E1','C9B',B2,FP_F47));  A(R('R21','6k8','C9B','INV1B',B2))
A(C('C10','4u7','E2','C10B',B2,FP_F47));A(R('R22','6k8','C10B','NINV1B',B2))
A(R('R23','22k','INV1B','SIG-VCA',B2));A(C('C11','100p','INV1B','SIG-VCA',B2))
A(R('R24','22k','NINV1B','AGND',B2))
A(OA('U1',2,{'5':'NINV1B','6':'INV1B','7':'SIG-VCA'},B2))

# ---------------- Sheet 3 : makeup, output, aux ----------------
B3='SH3 MAKEUP, OUTPUT DRIVERS AND AUX'
A(OA('U2',1,{'3':'SIG-VCA','2':'INV2A','1':'OUT-A'},B3))
A(POT('RV2','10k','INV2A','OUT-A','OUT-A',B3))
A(R('R26','1k','INV2A','AGND',B3));    A(R('R28','100R','OUT-A','BYP-A',B3))
A(R('R29','10k','OUT-A','INV2B',B3));  A(R('R30','10k','INV2B','OUT-B',B3))
A(C('C13','100p','INV2B','OUT-B',B3)); A(R('R31','5k1','NINV2B','AGND',B3))
A(OA('U2',2,{'5':'NINV2B','6':'INV2B','7':'OUT-B'},B3))
A(R('R32','100R','OUT-B','BYP-B',B3))
A(('SW1','Switch','SW_DPDT_x2','BYPASS','',B3,{'2':'OUT+','1':'BYP-A','3':'IN+'},1))
A(('SW1','Switch','SW_DPDT_x2','BYPASS','',B3,{'5':'OUT-','4':'BYP-B','6':'IN-'},2))
A(R('R80','22k','AUXIN-','INV5A',B3)); A(R('R81','22k','AUXIN+','NINV5A',B3))
A(R('R82','22k','INV5A','KEY',B3));    A(R('R83','22k','NINV5A','AGND',B3))
A(OA('U5',1,{'3':'NINV5A','2':'INV5A','1':'KEY'},B3))
A(OA('U5',2,{'5':'OUT-A','6':'AUXBUF','7':'AUXBUF'},B3))
A(R('R33','100R','AUXBUF','AUXOUT+',B3)); A(R('R34','100R','AGND','AUXOUT-',B3))

# ---------------- Sheet 4 : sidechain ----------------
B4='SH4 SIDECHAIN DETECTOR'
A(('SW2','Switch','SW_SPDT','INT/EXT','',B4,{'2':'SCSEL','1':'SIG-VCA','3':'KEY'},1))
A(OA('U6',2,{'5':'SCSEL','6':'SCBUF','7':'SCBUF'},B4))
A(C('C14','2u2','SCBUF','SCF',B4,FP_F22))
A(('SW3','Switch','SW_SPST','HPF DEFEAT','',B4,{'1':'SCBUF','2':'SCF'},1))
A(R('R38','1k','SCF','AGND',B4))
A(POT('RV3','100kA','SCF','RV3O','RV3O',B4))
A(R('R35','1k','RV3O','INV3A',B4));   A(R('R36','82k','INV3A','SC-AMP',B4))
A(R('R37','47k','NINV3A','AGND',B4))
A(OA('U3',1,{'3':'NINV3A','2':'INV3A','1':'SC-AMP'},B4))
A(R('R39','10k','SC-AMP','S1',B4));    A(R('R41','10k','NINV3B','AGND',B4))
A(D('D5','1N4148','S1','U3BO',B4));    A(D('D6','1N4148','U3BO','XN',B4))
A(R('R40','10k','S1','XN',B4))
A(OA('U3',2,{'5':'NINV3B','6':'S1','7':'U3BO'},B4))
A(R('R42','20k','SC-AMP','S2',B4));    A(R('R43','10k','XN','S2',B4))
A(R('R44','20k','S2','RECT',B4));      A(R('R49','5k1','NINV4A','AGND',B4))
A(OA('U4',1,{'3':'NINV4A','2':'S2','1':'RECT'},B4))
A(POT('RV4','100k','RECT','RATW','AGND',B4))
A(R('R45','220R','RATW','LINKN',B4))
A(('SW4','Switch','SW_SPST','LINK','',B4,{'1':'LINKN','2':'LINK'},1))
A(POT('RV5','10k','LINKN','ATKO','ATKO',B4))
A(R('R46','47R','ATKO','D7K',B4));     A(D('D7','1N4148','CTRL','D7K',B4))
A(C('C15','10u','CTRL','AGND',B4,FP_F10))
A(POT('RV6','1M','CTRL','RELO','RELO',B4))
A(R('R47','15k','RELO','AGND',B4))
A(OA('U4',2,{'5':'CTRL','6':'INV4B','7':'CTRL-B'},B4))
A(R('R74','220k','INV4B','CTRL-B',B4))

# ---------------- Sheet 5 : power, references, meter ----------------
B5='SH5 POWER, REFERENCES AND METER'
A(R('R50','10R','+16V-IN','+16V',B5)); A(CP('C16','100u','+16V','AGND',B5))
A(D('D8','1N4004','AGND','+16V',B5,FP_D4))
A(R('R51','10R','-16V-IN','-16V',B5)); A(CP('C17','100u','AGND','-16V',B5))
A(D('D9','1N4004','-16V','AGND',B5,FP_D4))
A(R('R53','1k8','-16V','-5V1',B5));    A(Z('D10','BZX79-C5V1','-5V1','AGND',B5))
A(CP('C19','47u','AGND','-5V1',B5));   A(C('C20','100n','-5V1','AGND',B5))
A(R('R9','68k','+16V','VBIAS',B5));    A(R('R10','11k','VBIAS','AGND',B5))
A(CP('C6','100u','VBIAS','AGND',B5));  A(C('C7','100n','VBIAS','AGND',B5))
A(R('R60','24k','+16V','VREF5',B5));   A(R('R61','1k33','VREF5','VREFA',B5))
A(R('R62','23k2','VREFA','AGND',B5))
A(CP('C21','47u','VREF5','AGND',B5));  A(CP('C22','4u7','VREFA','AGND',B5))
A(R('R68','1k','VREF5','STB',B5));     A(R('R69','36k','STB','CTRL-B',B5))
A(OA('U6',1,{'3':'VREFA','2':'STA','1':'STA'},B5))
A(R('R77','3k9','AGND','LED-A',B5))
A(('LED1','Device','LED','GR','LED_THT:LED_D3.0mm',B5,{'2':'LED-A','1':'CTRL-B'}))
A(R('R52','100R','CHASSIS','AGND',B5)); A(C('C18','10n','CHASSIS','AGND',B5))
A(R('R48','0R','PGND','AGND',B5))

# ---------------- Sheet 6 : LED meters ----------------
# Two 7-segment bargraphs. A discrete comparator ladder would need 14 op-amp sections -
# seven more NE5532s, ~56 mA - which the 130 mA rack budget cannot carry, so this is the
# one place the NE5532/BC549 palette is broken. Both drivers run in DOT mode (MODE pin
# open): exactly one LED is lit per meter, which is what keeps the current affordable.
# Both are LM3914s (linear). The level meter was an LM3915 (3 dB steps) until October 2026,
# when it could not be bought; U9's LEDs moved to outputs 1-7, which reads 17 dB in finer
# steps near the top (see U9 below).
B7='SH6 LED METERS'
FP_LM  = 'Package_DIP:DIP-18_W7.62mm'
FP_LED2= 'LED_THT:LED_D2.0mm_W4.0mm_H2.8mm_FlatTop'
def LM(ref,val,pins):  return (ref,'Driver_LED','LM3914N',val,FP_LM,B7,pins)
def ML(ref,cath):      return (ref,'Device','LED','meter',FP_LED2,B7,{'2':'+16V','1':cath})

# -- gain-reduction channel: CTRL-B rests at 0 V and goes negative with gain reduction,
#    so it needs inverting before a meter can read it. RV7 sets full-scale deflection.
# Gain vs control voltage is a sigmoid (Q6/Q7 are an undegenerated pair), so a meter that
# steps evenly in volts puts three of its seven segments inside the first 2 dB. R93 subtracts
# a fixed offset first, which lands the seven steps near 1/2/3/6/9/14/19 dB instead. That
# leaves U7B sitting at -2.1 V with no compression, so D12 clamps the driver input at -0.7 V.
A(R('R84','10k','CTRL-B','INV7B',B7));  A(R('R85','10k','NINV7B','AGND',B7))
A(R('R93','18k','GRREF','INV7B',B7))
A(POT('RV7','20k','INV7B','GR-SIG','GR-SIG',B7,FP_TRM))
A(OA('U7',2,{'5':'NINV7B','6':'INV7B','7':'GR-SIG'},B7))
A(R('R94','10k','GR-SIG','GRIN',B7)); A(D('D12','1N4148','AGND','GRIN',B7))

# -- level channel: peak detector off the makeup output. D11 inside the loop means the
#    op-amp servos out its own forward drop; R87 limits the charging surge into C35.
A(POT('RV8','20k','OUT-A','LVLTRM','AGND',B7,FP_TRM))
A(R('R86','10k','LVLTRM','MTRIN',B7))
A(OA('U7',1,{'3':'MTRIN','2':'PKDET','1':'U7AO'},B7))
A(R('R87','1k','U7AO','D11A',B7));      A(D('D11','1N4148','D11A','PKDET',B7))
A(C('C35','2u2','PKDET','AGND',B7,FP_F22))
A(R('R88','100k','PKDET','AGND',B7))    # 220 ms decay - meter ballistics, not a detector

# -- U8 gain reduction, LM3914 linear, LEDs on outputs 1-7 so the first segment lights
#    at the smallest useful gain reduction. Outputs 8-10 are unused.
A(LM('U8','LM3914',{'3':'+16V','2':'AGND','5':'GRIN','6':'GRREF','7':'GRREF',
                    '4':'AGND','8':'GRADJ','9':'GR-MODE-NC',
                    '1':'GRL1','18':'GRL2','17':'GRL3','16':'GRL4','15':'GRL5',
                    '14':'GRL6','13':'GRL7',
                    '12':'GR-NC8','11':'GR-NC9','10':'GR-NC10'}))
A(R('R89','2k7','GRREF','GRADJ',B7));   A(R('R90','8k2','GRADJ','AGND',B7))

# -- U9 output level, LM3914 linear, LEDs on outputs 1-7. With RLO at ground the thresholds
#    are 1/7, 2/7 ... 7/7 of the top one: -17, -11, -7.4, -4.9, -2.9, -1.3 and 0 dB, so the
#    meter still spans 17 dB and reads finest near clipping. Outputs 8-10 join the top LED:
#    in dot mode only the highest lit output sinks, and without them the meter would go dark
#    on an over.
A(LM('U9','LM3914',{'3':'+16V','2':'AGND','5':'PKDET','6':'LVLREF','7':'LVLREF',
                    '4':'AGND','8':'LVLADJ','9':'LVL-MODE-NC',
                    '1':'LVLL1','18':'LVLL2','17':'LVLL3','16':'LVLL4','15':'LVLL5',
                    '14':'LVLL6','13':'LVLL7','12':'LVLL7','11':'LVLL7','10':'LVLL7'}))
A(R('R91','2k7','LVLREF','LVLADJ',B7)); A(R('R92','8k2','LVLADJ','AGND',B7))

# -- the two LED columns. D20 and D30 are the first segment of each to light; refdes match
#    the panel drawing in panel/make_panel.py.
for i in range(7):
    A(ML('D%d'%(20+i),'GRL%d'%(i+1)))
    A(ML('D%d'%(30+i),'LVLL%d'%(i+1)))

# -- U7 supply pins and local decoupling. C38 is bulk for the switching LED current.
A(OA('U7',3,{'8':'+16V','4':'-16V'},B7))
A(C('C36','100n','+16V','AGND',B7));    A(C('C37','100n','+16V','AGND',B7))
A(CP('C38','47u','+16V','AGND',B7))
A(C('C39','100n','+16V','AGND',B7));    A(C('C40','100n','-16V','AGND',B7))

# ---------------- op-amp power units + decoupling ----------------
B6='SH5 SUPPLY DECOUPLING'
for u in ['U1','U2','U3','U4','U5','U6']:
    A(OA(u,3,{'8':'+16V','4':'-16V'},B6))
for i,u in enumerate(['U1','U2','U3','U4','U5','U6']):
    A(C('C%d'%(23+i),'100n','+16V','AGND',B6))
    A(C('C%d'%(29+i),'100n','-16V','AGND',B6))

# power flags so ERC knows the rails are driven
for i,(net) in enumerate(['+16V','-16V','AGND','-5V1']):
    A(('#FLG%d'%i,'power','PWR_FLAG','PWR_FLAG','',B6,{'1':net}))

NO_CONNECT = (['P48-NC', 'GR-MODE-NC', 'LVL-MODE-NC']       # MODE open = dot mode
              + ['GR-NC8', 'GR-NC9', 'GR-NC10'])            # LM3914 outputs 8-10 unused
