"""Steer 500 compressor - authoritative netlist.
Each entry: (ref, lib, symname, value, footprint, block, {pin: net})
Op-amp packages appear as three units: A (unit1), B (unit2), P (unit3 = power pins).
"""
FP_R   = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
FP_CC  = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
FP_CF  = 'Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm'
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
A(C('C5','10u','PAD','Q1B',B2,FP_CF)); A(R('R11','10k','Q1B','VBIAS',B2))
A(Q('Q1','EA','Q1B','Q1E',B2));        A(R('R14','220R','Q1E','TAIL',B2))
A(Q('Q2','EB','Q2B','Q2E',B2));        A(R('R15','220R','Q2E','TAIL',B2))
A(R('R12','10k','Q2B','VBIAS',B2));    A(R('R13','220R','Q2B','C8A',B2))
A(C('C8','10u','C8A','AGND',B2,FP_CF))
A(Q('Q3','TAIL','AGND','Q3E',B2));     A(R('R18','1k5','Q3E','-5V1',B2))
A(Q('Q6','+16V','STA','EA',B2));       A(Q('Q7','CP','STB','EA',B2))
A(Q('Q8','+16V','STA','EB',B2));       A(Q('Q9','CN','STB','EB',B2))
A(R('R16','4k7','+16V','CP',B2));      A(R('R17','4k7','+16V','CN',B2))
A(Q('Q4','+16V','CP','E1',B2));        A(Q('Q5','+16V','CN','E2',B2))
A(R('R19','10k','E1','AGND',B2));      A(R('R20','10k','E2','AGND',B2))
A(C('C9','2u2','E1','C9B',B2,FP_CF));  A(R('R21','3k3','C9B','INV1B',B2))
A(C('C10','2u2','E2','C10B',B2,FP_CF));A(R('R22','3k3','C10B','NINV1B',B2))
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
A(C('C14','220n','SCBUF','SCF',B4,FP_CF))
A(('SW3','Switch','SW_SPST','HPF DEFEAT','',B4,{'1':'SCBUF','2':'SCF'},1))
A(R('R38','10k','SCF','AGND',B4))
A(POT('RV3','1M','SCF','RV3O','RV3O',B4))
A(R('R35','20k','RV3O','INV3A',B4));   A(R('R36','100k','INV3A','SC-AMP',B4))
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
A(POT('RV5','4k7','LINKN','ATKO','ATKO',B4))
A(R('R46','47R','ATKO','D7K',B4));     A(D('D7','1N4148','CTRL','D7K',B4))
A(C('C15','10u','CTRL','AGND',B4,FP_CF))
A(POT('RV6','220k','CTRL','RELO','RELO',B4))
A(R('R47','4k7','RELO','AGND',B4))
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
A(R('R60','47k','+16V','VREF5',B5));   A(R('R61','1k33','VREF5','VREFA',B5))
A(R('R62','23k2','VREFA','AGND',B5))
A(CP('C21','47u','VREF5','AGND',B5));  A(CP('C22','47u','VREFA','AGND',B5))
A(R('R68','1k','VREF5','STB',B5));     A(R('R69','36k','STB','CTRL-B',B5))
A(OA('U6',1,{'3':'VREFA','2':'STA','1':'STA'},B5))
A(R('R77','3k9','AGND','LED-A',B5))
A(('LED1','Device','LED','GR','LED_THT:LED_D3.0mm',B5,{'2':'LED-A','1':'CTRL-B'}))
A(R('R52','100R','CHASSIS','AGND',B5)); A(C('C18','10n','CHASSIS','AGND',B5))
A(R('R48','0R','PGND','AGND',B5))

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

NO_CONNECT = ['P48-NC']
