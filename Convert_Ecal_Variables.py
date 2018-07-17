import os
import sys
import math as m
import numpy as n
import ROOT as r
import os.path
import os
from scipy.signal import argrelextrema, savgol_filter, find_peaks_cwt, argrelmax

from ROOT import gSystem
result=gSystem.Load("libDDCorePlugins")
from ROOT import dd4hep
if result < 0:
    print "No lib loadable!"

system_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4")
ecalBarrel_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,cryo:1,type:3,subtype:3,layer:8,eta:9,phi:10")
hcalBarrel_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,module:8,row:9,layer:5")
hcalExtBarrel_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,module:8,row:9,layer:5")
ecalEndcap_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,subsystem:1,type:3,subtype:3,layer:8,eta:10,phi:10")
hcalEndcap_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,subsystem:1,type:3,subtype:3,layer:8,eta:10,phi:10")
ecalFwd_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,subsystem:1,type:3,subtype:3,layer:8,eta:11,phi:10")
hcalFwd_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,subsystem:1,type:3,subtype:3,layer:8,eta:11,phi:10")
trackerBarrel_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,layer:5,module:18,x:-15,z:-15")
trackerEndcap_decoder = dd4hep.DDSegmentation.BitFieldCoder("system:4,posneg:1,disc:5,component:17,x:-15,z:-15")

lastECalBarrelLayer = int(7)
lastECalEndcapLayer = int(39)
lastECalFwdLayer = int(41)

def systemID(cellid):
    return system_decoder.get(cellid, "system")

def benchmarkCorr(ecal, ecal_last, ehad, ehad_first):
    a=0.978
    b=0.479
    c=-0.0000054
    ebench = ecal*a + ehad + b * math.sqrt(math.fabs(a*ecal_last*ehad_first)) + c*(ecal*a)**2
    return ebench

def signy(y):
    if y>0: return 1
    elif y<0: return -1
    return 0

def Shower_width(Energies, Cellids, wxst):

    strips = n.unique(Cellids)
    top = 0
    bot = 0
    cellenergies = n.zeros(len(strips),dtype=float)
    i = 0

    try:
        for cell in strips:
            cellenergies[n.where(strips == cell)[0][0]] = sum(Energies[n.where(Cellids == cell)[0]])

    except(ValueError):

        return "NaN"

    imax = int(strips[n.argmax(cellenergies)])

    for i in strips:

        try:
            if int(i) > (imax - wxst) and int(i) < (imax + wxst):
                top += sum(Energies[n.where(Cellids == i)[0]])*(((int(i)-imax)**2))
                bot += sum(Energies[n.where(Cellids == i)[0]])
            else:
                continue

        except(IndexError):

            top += 0
            bot += 0

        i += 1

	Wnst = m.sqrt((top/bot))
    #print Wnst
    return Wnst

def edmaxy(Emax,E2ndmax,Cellids,Energies):

    try:
        strip2max = Cellids[n.where(Energies == E2ndmax)[0][0]]
        stripmax = Cellids[n.where(Energies == Emax)[0][0]]
        #print stripmax, strip2max
    except(IndexError):
        print "indexerror"
        return 0

    strip2E = 0.
    stripminE = []
    i = 0

    while i < len(Cellids):

        if Cellids[i] == strip2max:
            strip2E += Energies[i]

        if (Cellids[i] > strip2max and Cellids[i] < stripmax) or (Cellids[i] > stripmax and Cellids[i] < strip2max):
            stripminE.append(Energies[i])

        i += 1

    if stripminE == []:

        return 0.

    else:

        nstripminE = n.array(stripminE)
        minE = n.amin(nstripminE)

    '''stripmin = Cellids[n.where(Energies == minE)[0][0]]
    #print stripmin
    #print stripmin, stripmax, strip2max
    minstripE = 0.
    i = 0

    while i < len(Cellids):

        if Cellids[i] == stripmin:
            minstripE += Energies[i]

        i += 1'''

    edmax = E2ndmax - minE
    return edmax

def eocorey(Emax,Cellids,Energies):
    try:
        cells = n.unique(Cellids)
        cellenergies = n.zeros(len(cells),dtype=float)
        for cell in cells:
            cellenergies[n.where(cells == cell)[0][0]] = sum(Energies[n.where(Cellids == cell)[0]])
        stripmax = int(cells[n.argmax(cellenergies)])
    except(IndexError):
        return 0
    E3 = 0.
    E1 = 0.
    i = 0

    while i < len(Cellids):

        if int(Cellids[i]) <= stripmax + 3 and int(Cellids[i]) >= stripmax - 3:
            E3 += Energies[i]

            if int(Cellids[i]) >= stripmax - 1 and int(Cellids[i]) <= stripmax + 1:
                E1 += Energies[i]

        i += 1

    eocore = (E3 - E1) / E1
    return eocore

def savitzky_golay(y, window_size, order, deriv=0, rate=1):

    import numpy as np
    from math import factorial

    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve( m[::-1], y, mode='valid')

ev_num = n.zeros(1, dtype=int)
ev_nRechits = n.zeros(1, dtype=int)
e2max = n.zeros(1, dtype=float)
emax = n.zeros(1, dtype=float)
edmax = n.zeros(1, dtype=float)
eocore = n.zeros(1, dtype=float)
w3st = n.zeros(1, dtype=float)
w21st = n.zeros(1, dtype=float)

if len(sys.argv)!=3:
    print 'usage python Convert.py infile outfile'
infile_name = sys.argv[1]
outfile_name = sys.argv[2]

current_dir = os.getcwd()

if os.path.isfile(outfile_name) == False:
    infile=r.TFile.Open(infile_name)
    intree=infile.Get('events')

    maxEvent = intree.GetEntries()
    print 'Number of events : ',maxEvent

    outfile=r.TFile(outfile_name,"recreate")
    outtree=r.TTree('events','Events')

    # Branches for the discriminating variables of the ecal detector.

    outtree.Branch("e2max", e2max, "e2max/D")
    outtree.Branch("emax", emax, "emax/D")
    outtree.Branch("edmax", edmax, "edmax/D")
    outtree.Branch("eocore", eocore, "eocore/D")
    outtree.Branch("w3st", w3st, "w3st/D")
    outtree.Branch("w21st", w21st, "w21st/D")


else:
    infile=r.TFile.Open(infile_name)
    intree=infile.Get('events')
    outfile=r.TFile.Open(outfile_name,"update")
    outtree=outfile.Get('events')

    maxEvent = intree.GetEntries()
    print 'Number of events : ',maxEvent

    # Branches for the discriminating variables of the ecal detector.

    outtree.SetBranchAddress("e2max", e2max)
    outtree.SetBranchAddress("emax", emax)
    outtree.SetBranchAddress("edmax", edmax)
    outtree.SetBranchAddress("eocore", eocore)
    outtree.SetBranchAddress("w3st", w3st)
    outtree.SetBranchAddress("w21st", w21st)

numEvent = 0
for event in intree:
    ev_num[0] = numEvent
    numHits = 0
    E = .0
    calE = 0
    cal1E = 0
    Ecal_Phi = []
    Ecal_cell = []
    Ecal1_E = []
    Ecal_Eta = []
    cal1Emax = -1.
    cal1E2max = -1.
    cal1Etamax = -1.
    cal1Eta2max = -1.
    cal1Phimax = -1.
    cal1Phi2max = -1.

    for c in event.ECalBarrelCells:

        if ecalBarrel_decoder.get(c.core.cellId, "layer") == 1:

            Eta = ecalBarrel_decoder.get(c.core.cellId, "eta")
            cal1E = c.core.energy
            eta = int(Eta) - 169*0.01
            Phi = ecalBarrel_decoder.get(c.core.cellId, "phi")
            Ecal_Eta.append(Eta)
            Ecal_cell.append(int(str(Eta)+str(Phi)))
            Ecal1_E.append(cal1E)
            Ecal_Phi.append(Phi)

            if cal1E >= cal1Emax or cal1E > cal1E2max:

                if len(Ecal1_E) < 2:

                    cal1Emax = cal1E
                    cal1Etamax = Eta
                    cal1Phimax = Phi

                elif cal1E > cal1Emax:

                    if Phi != Ecal_Phi[Ecal1_E.index(cal1Emax)]:

                        cal1E2max = cal1Emax
                        cal1Eta2max = cal1Etamax
                        cal1Phi2max = cal1Phimax
                        cal1Emax = cal1E
                        cal1Etamax = Eta
                        cal1Phimax = Phi

                    else:

                        cal1Emax = cal1E
                        cal1Etamax = Eta
                        Cal1Phimax = Phi

                else:

                    cal1E2max = cal1E
                    cal1Eta2max = Eta
                    cal1Phi2max = Phi


        numHits += 1

    Cellids = n.array(Ecal_cell)
    Energies = n.array(Ecal1_E)
    Etas = n.array(Ecal_Eta)
    Phis = n.array(Ecal_Phi)

    '''if len(Energies) > 17:
        smoothenergies = savgol_filter(Energies,17,4)
    #    smoothenergies = savgol_filter(Energies,17,4)
    elif len(Energies)%2 == 0:
        smoothenergies = savgol_filter(Energies,len(Energies)-1,4)
    else:
        smoothenergies = savgol_filter(Energies,len(Energies),4)

    print len(smoothenergies), len(Energies)'''

    MaxInd = argrelextrema(Energies, n.greater)
    MaxInd2 = find_peaks_cwt(Energies,n.arange(1,5))

    Maxes = n.sort(Energies[MaxInd])
    Maxes2 = n.sort(Energies[MaxInd2])
    print Maxes
    print Maxes2
    print n.amax(Maxes)

    if n.amax(Maxes) > cal1Emax:
        cal1Emax = n.amax(Maxes)
        cal1Phimax = Phis[n.where(Energies == cal1Emax)[0][0]]


    if n.float(n.amax(Maxes)) < n.float(cal1Emax):
        if n.float(n.amax(Maxes)) > n.float(cal1E2max):
            print "found"
            cal1E2max = n.amax(Maxes)
            cal1Phi2max = Phis[n.where(Energies == cal1E2max)[0][0]]

    else:

        cal1E2max = Maxes[len(Maxes)-2]
        cal1Phi2max = Phis[n.where(Energies == cal1E2max)[0][0]]


   # if cal1Emax == 0. or cal1E2max == 0:
       # print cal1Emax, cal1E2max, Energies
    #print "All recorded energies: ", Energies
    #print Cellids, "\n", n.unique(Cellids)
    print "No. of energies: ", len(Energies), "No. of cells: ", len(Phis), "No. of unique cells: ", len(n.unique(Phis))
    print "1st maximum: ", cal1Emax, "and cell: ", cal1Phimax
    print "2nd maximum: ", cal1E2max, "and cell: ",  cal1Phi2max
    '''print "The energies using numpy.where: 1st max: ", Energies[n.where(Energies == cal1Emax)[0][0]], "2nd max: ",Energies[n.where(Energies == cal1E2max)[0][0]]
    print "The cells using numpy.where: 1st max cell: ", Cellids[n.where(Energies == cal1Emax)[0][0]], "2nd max cell: ", Cellids[n.where(Energies == cal1E2max)[0][0]]
    ev_nRechits[0] = numHits
    print "\n"
    print "test n.where: ", Cellids[n.where(Energies == cal1Emax)[0]], Energies[n.where(Energies == cal1Emax)[0]]'''
    print "\n"
    if len(Energies) > 2:
        w3st[0] = Shower_width(Energies, Phis, 3)
        w21st[0] = Shower_width(Energies, Phis, 21)
        eocore[0] = eocorey(cal1Emax, Phis, Energies)
        e2max[0] = cal1E2max
        emax[0] = cal1Emax
        edmax[0] = edmaxy(cal1Emax, cal1E2max, Phis, Energies)
    else:
        continue

    outtree.Fill()

    numEvent += 1

outtree.Write()
outfile.Write()
outfile.Close()
