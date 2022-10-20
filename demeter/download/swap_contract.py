from ._typing import OnchainTxType
from .utils import HexUtil


class Constant(object):
    MINT_KECCAK = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
    SWAP_KECCAK = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    BURN_KECCAK = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
    COLLECT_KECCAK = "0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0"


type_dict = {Constant.MINT_KECCAK: OnchainTxType.MINT,
             Constant.SWAP_KECCAK: OnchainTxType.SWAP,
             Constant.BURN_KECCAK: OnchainTxType.BURN,
             Constant.COLLECT_KECCAK: OnchainTxType.COLLECT}


def decode_address_from_topic(topic_str):
    return "0x" + topic_str[26:]


def handle_event(topics_str, data_hex):
    # proprocess topics string -> topic list
    # topics_str = topics.values[0]
    sqrtPriceX96 = receipt = amount1 = current_liquidity = current_tick = tick_lower = tick_upper = delta_liquidity = None
    if isinstance(topics_str, str):
        topic_list = topics_str.strip("[]").replace("'", "").replace(" ", "").split("\n")
    else:
        topic_list = topics_str

    # data_hex = data.values[0]

    type_topic = topic_list[0]
    tx_type = type_dict[type_topic]
    no_0x_data = data_hex[2:]
    chunk_size = 64
    chunks = len(no_0x_data)

    if tx_type == OnchainTxType.SWAP:
        sender = decode_address_from_topic(topic_list[1])
        receipt = decode_address_from_topic(topic_list[2])
        split_data = ["0x" + no_0x_data[i:i + chunk_size] for i in range(0, chunks, chunk_size)]
        amount0, amount1, sqrtPriceX96, current_liquidity, current_tick = [HexUtil.to_signed_int(onedata) for onedata in
                                                                           split_data]
    elif tx_type == OnchainTxType.BURN:
        sender = decode_address_from_topic(topic_list[1])
        tick_lower = HexUtil.to_signed_int(topic_list[2])
        tick_upper = HexUtil.to_signed_int(topic_list[3])
        split_data = ["0x" + no_0x_data[i:i + chunk_size] for i in range(0, chunks, chunk_size)]
        delta_liquidity, amount0, amount1 = [HexUtil.to_signed_int(onedata) for onedata in split_data]
        delta_liquidity = -delta_liquidity
    elif tx_type == OnchainTxType.MINT:
        # sender = topic_str_to_address(topic_list[1])
        owner = decode_address_from_topic(topic_list[1])
        tick_lower = HexUtil.to_signed_int(topic_list[2])
        tick_upper = HexUtil.to_signed_int(topic_list[3])
        split_data = ["0x" + no_0x_data[i:i + chunk_size] for i in range(0, chunks, chunk_size)]
        sender = decode_address_from_topic(split_data[0])
        delta_liquidity, amount0, amount1 = [HexUtil.to_signed_int(onedata) for onedata in split_data[1:]]
    elif tx_type == OnchainTxType.COLLECT:
        tick_lower = HexUtil.to_signed_int(topic_list[2])
        tick_upper = HexUtil.to_signed_int(topic_list[3])
        split_data = ["0x" + no_0x_data[i:i + chunk_size] for i in range(0, chunks, chunk_size)]
        sender = decode_address_from_topic(split_data[0])
        amount0, amount1 = [HexUtil.to_signed_int(onedata) for onedata in split_data[1:]]
    else:
        raise ValueError("not support tx type")

    return tx_type, sender, receipt, amount0, amount1, sqrtPriceX96, current_liquidity, current_tick, tick_lower, tick_upper, delta_liquidity
