import hashlib
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
logger_sh = logging.StreamHandler()
formatter = logging.Formatter('%(name)s [%(levelname)s] %(message)s')
logger_sh.setFormatter(formatter)
logger.addHandler(logger_sh)

from sage.all import *
proof.all(False)

try:
    from . import params, ec, hd, misc
    from . import quaternions as qt
    from . import qlapoti as qlpt
except ImportError:
    import params, ec, hd, misc
    import quaternions as qt
    import qlapoti as qlpt

class SQIsignTriangle:

    def __init__(self):
        # Key generation
        self.pk, self.sk = self.key_gen()

    def key_gen(self):
        """
        Key generation [Alg 2]
        Output:
        - sk: secret key
        - pk: public key
        """
        logger.info('Starting keygen')
        _t0 = time.time()

        I_sk = qt.RandomIdealGivenNorm(params.D_mix, True)
        # assert I_sk.left_order() == params.O0 and I_sk.norm() == params.D_mix

        I_sk = qt.RandomEquivalentPrimeIdeal(I_sk)

        _t1 = time.time()
        logger.info(f'- Ideal generation done: {_t1-_t0:.3f}s')

        E_pk, phi_P0, phi_Q0 = qlpt.IdealToIsogeny(I_sk)

        _t2 = time.time()
        logger.info(f'- Qlapoti done: {_t2-_t1:.3f}s')

        P_pk, Q_pk = ec.TorsionBasis(E_pk)
        M_sk = ec.ChangeOfBasis((phi_P0, phi_Q0), (P_pk, Q_pk))
        # assert ec.EvalMatrix(M_sk, (phi_P0, phi_Q0)) == (P_pk, Q_pk)

        pk = (E_pk, (P_pk, Q_pk))
        sk = (E_pk, (P_pk, Q_pk), I_sk, M_sk)

        _t3 = time.time()
        logger.info(f'- Change of basis done: {_t3-_t2:.3f}s')
        logger.info(f'Keygen done: {_t3-_t0:.3f}s')

        return pk, sk

    def sign(self, msg):
        """
        Signing 
        Input:
        - msg: the message
        Output:
        - sigma: a valid signature
        """
        logger.info('Starting signing')
        _t0 = time.time()

        E_pk, (P_pk, Q_pk), I_sk, M_sk = self.sk

        # Commitment [Alg 3].
        I_com = qt.RandomIdealGivenNorm(params.D_mix, True)
        I_com = qt.RandomEquivalentPrimeIdeal(I_com)

        E_com, P_com, Q_com = qlpt.IdealToIsogeny(I_com)
        _t1 = time.time()
        logger.info(f'- Commitment done: {_t1-_t0:.3f}s')

        # Challenge
        enc_pk = misc.encode_curve_a(E_pk)
        enc_com = misc.encode_curve_j(E_com)
        if type(msg) == str: msg = msg.encode()

        chl = enc_pk + enc_com + msg
        c1,c2 = prime_hash(chl)

        _t2 = time.time()
        logger.info(f'- Challenge computed: {_t2-_t1:.3f}s')

        # Response [Alg 4].
        # - challenge to ideal
        I_rsp1 = I_sk.conjugate() * I_com
        while True:
            I_rsp, k = qt.EquivalentSpecialIdeal(I_rsp1, c1, c2)
            q = I_rsp.norm()
            e_rsp = ZZ(q).bit_length()
            if q%2 == 1 and gcd(q, 2**e_rsp - q) == 1:
                break

        # - compute auxiliary isogeny
        I_aux = qt.RandomIdealGivenNorm(2**e_rsp - q, False)
        I_sk_rsp = I_sk * I_rsp
        I_cra =  I_sk_rsp.intersection(I_aux)
        E_aux, P_aux, Q_aux = qlpt.IdealToIsogeny(I_cra)
        (P_aux, Q_aux) = ec.EvalMatrix(M_sk, (P_aux, Q_aux))
        P_aux = 2**(params.f - e_rsp) * P_aux
        Q_aux = 2**(params.f - e_rsp) * Q_aux
        
        # - signature
        sigma = (P_aux, Q_aux, q)
        
        _t3 = time.time()
        logger.info(f'sign done: {_t3-_t0:.3f}s')

        return sigma
    
def prime_hash(msg, lvl=1):
    if lvl == 1:
        byte_len = 8   # 64 bits
    elif lvl == 3:
        byte_len = 12  # 96 bits
    elif lvl == 5:
        byte_len = 16  # 128 bits
    else:
        raise ValueError("The lvl parameter must be 1, 3, or 5.")
    
    digest_size = byte_len * 2
    chl = hashlib.shake_256(msg).digest(digest_size)
    
    while True:
        c1 = int.from_bytes(chl[:byte_len], 'big')
        c2 = int.from_bytes(chl[byte_len:], 'big')
        
        if is_prime(c1):
            return c1, c2
        # ensure c1 is prime
        elif is_prime(c2):
            return c2, c1
        else:
            chl = hashlib.shake_256(chl).digest(digest_size)    
    
def SQIsignTriangle_verify(msg, sigma, pk):
    """
    Verification [Algorithm 5]
    Input:
    - msg: message
    - sigma: signature
    - pk: public key
    Output:
    - boolean verification
    """
    logger.info('Starting verification')
    _t0 = time.time()
    E_pk, (P_pk, Q_pk) = pk
    (P_aux, Q_aux, q) = sigma

    # [q]*(P_pk, Q_pk)
    e_rsp = ZZ(q).bit_length()
    P_pk = 2**(params.f - e_rsp) * q * P_pk
    Q_pk = 2**(params.f - e_rsp) * q * Q_pk
    
    _t1 = time.time()
    # compute and evaluate the (2^e_rsp, 2^e_rsp)-isogeny
    K = ((P_pk, P_aux), (Q_pk, Q_aux))
    Phi = hd.Dim2Iso(K, e_rsp)
    E1, E2 = Phi.codomain()
    _t2 = time.time()
    logger.info(f'HD isogeny: {_t2-_t1:.3f}s')

    enc_pk = misc.encode_curve_a(E_pk)
    enc_E1 = misc.encode_curve_j(E1)
    enc_E2 = misc.encode_curve_j(E2)
    if type(msg) == str: msg = msg.encode()

    # check if E1 or E2 = E_com and if deg(phi_1) or deg(phi_2) = q
    chl1 = enc_pk + enc_E1 + msg
    chl2 = enc_pk + enc_E2 + msg
    c1,c2 = prime_hash(chl1)
    c3,c4 = prime_hash(chl2)

    if (q-c2)%c1 == 0 or (q-c4)%c3 == 0:
        _t3 = time.time()
        logger.info(f'Verification done: {_t3-_t0:.3f}s')
        return True
    else:
        return False
    
if __name__ == "__main__":
    # Add logging
    logger.setLevel(logging.DEBUG)

    rr = randint(1, 2**64)

    set_random_seed(rr)
    logger.debug(f'Running with seed {rr}')

    # Setting parameters [Sec 4.2]
    lvl = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    params.set_sqi_triangle_params(lvl)

    alice = SQIsignTriangle()

    msg = 'Hello world'
    sigma = alice.sign(msg)

    out = SQIsignTriangle_verify(msg, sigma, alice.pk)
    print(f'Verification: {out}')