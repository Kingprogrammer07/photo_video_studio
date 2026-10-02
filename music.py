"""music.py — original royalty-free piano beds. generate(kind, total, out).
kind: 'warm' (emotional) or 'bright' (light/modern)."""
import numpy as np, wave
SR=44100
def _add(buf,s,x):
    e=min(len(buf),int(s)+len(x))
    if e>int(s): buf[int(s):e]+=x[:e-int(s)]
def _piano(freq,dur,vel=0.5,decay=3.4):
    n=int(dur*SR);t=np.linspace(0,dur,n,False);w=np.zeros(n)
    for k,a in [(1,1.0),(2,0.5),(3,0.26),(4,0.14),(5,0.07)]:
        w+=a*np.sin(2*np.pi*freq*k*(1+0.0007*k*k)*t)
    env=np.ones(n);na=int(0.007*SR);env[:na]=np.linspace(0,1,na);env*=np.exp(-t*decay)
    return w*env*vel
def _bell(freq,dur,vel=0.15):
    n=int(dur*SR);t=np.linspace(0,dur,n,False)
    w=np.sin(2*np.pi*freq*t)+0.4*np.sin(2*np.pi*freq*2*t)
    return w*np.exp(-t*5.0)*vel
N={'C3':130.81,'D3':146.83,'E3':164.81,'F3':174.61,'G3':196.0,'A3':220.0,'B3':246.94,
 'C4':261.63,'D4':293.66,'E4':329.63,'F4':349.23,'F#4':369.99,'G4':392.0,'A4':440.0,'B4':493.88,
 'C5':523.25,'D5':587.33,'E5':659.25,'F5':698.46,'G5':783.99,'A5':880.0,'G2':98.0,'E3b':164.81}
WARM=[dict(b='G2',pad=['G3','D4'],arp=['G3','B3','D4','G4'],mel=['B4','D5','G4','B4']),
      dict(b='E3',pad=['E3','B3'],arp=['E3','G3','B3','E4'],mel=['G4','B4','E5','D5']),
      dict(b='C3',pad=['C3','G3'],arp=['C3','E3','G3','C4'],mel=['E4','G4','C5','E5']),
      dict(b='D3',pad=['D3','A3'],arp=['D3','F#4','A4','D5'],mel=['F#4','A4','D5','A4'])]
BRIGHT=[dict(b='C3',pad=['G3','C4'],arp=['C4','E4','G4','C5'],mel=['E5','G5','C5','E5']),
        dict(b='G3',pad=['G3','D4'],arp=['G3','B3','D4','G4'],mel=['D5','G5','B4','D5']),
        dict(b='A3',pad=['A3','E4'],arp=['A3','C4','E4','A4'],mel=['C5','E5','A4','C5']),
        dict(b='F3',pad=['F3','C4'],arp=['F3','A3','C4','F4'],mel=['A4','C5','F5','A4'])]
def _build(total,prog,beat,melf):
    BAR=beat*4;L=int((total+BAR+3)*SR);buf=np.zeros(L);pos=0.0;ci=0
    while pos<total:
        c=prog[ci%4];s=int(pos*SR)
        _add(buf,s,_piano(N[c['b']],BAR*0.98,0.36))
        for pn in c['pad']: _add(buf,s,_piano(N[pn],BAR*0.95,0.10))
        for j,an in enumerate(c['arp']*2):
            _add(buf,int((pos+j*beat/2)*SR),_piano(N[an],beat*0.85,0.18+0.02*(j%3)))
        for j,mn in enumerate(c['mel']):
            if j in (0,2): _add(buf,int((pos+j*beat)*SR),melf(N[mn],beat*1.5,0.2))
        pos+=BAR;ci+=1
    return buf[:int((total+1.4)*SR)]
def _reverb(x,wet,tail=1.4):
    irn=int(tail*SR);t=np.linspace(0,tail,irn,False)
    ir=np.random.normal(0,1,irn)*np.exp(-t*4.5);ir[0]=1.0;ir/=np.max(np.abs(ir))
    nf=1
    while nf<len(x)+irn:nf*=2
    w=np.fft.irfft(np.fft.rfft(x,nf)*np.fft.rfft(ir,nf))[:len(x)];w/=np.max(np.abs(w))+1e-9
    return (1-wet)*x/(np.max(np.abs(x))+1e-9)+wet*w
def generate(kind,total,out):
    if kind=='bright':
        dry=_build(total,BRIGHT,0.82,_bell); mix=_reverb(dry,0.22,1.1)
    else:
        dry=_build(total,WARM,0.95,lambda f,d,v:_piano(f,d,0.26)); mix=_reverb(dry,0.34,1.6)
    fi=int(1.0*SR);fo=int(1.9*SR)
    mix[:fi]*=np.linspace(0,1,fi);mix[-fo:]*=np.linspace(1,0,fo)
    mix/=np.max(np.abs(mix))+1e-9;mix*=0.9
    d=int(0.011*SR);Rc=np.concatenate([np.zeros(d),mix])[:len(mix)]
    st=np.clip(np.stack([mix,0.85*mix+0.15*Rc],1),-1,1)
    with wave.open(out,'w') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((st*32767).astype(np.int16).tobytes())
if __name__=='__main__':
    import sys; generate(sys.argv[1] if len(sys.argv)>1 else 'warm', 12.0, '/tmp/mtest.wav'); print('ok')
