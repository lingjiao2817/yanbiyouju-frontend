import logging
import os
import threading

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None
_device = None
_enabled: bool | None = None
_lock = threading.Lock()


def is_enabled() -> bool:
    global _enabled

    if _enabled is not None:
        return _enabled

    with _lock:
        if _enabled is not None:
            return _enabled

        if os.getenv("ENABLE_PERPLEXITY", "0") != "1":
            _enabled = False
            logger.info("困惑度评估未启用。")
            return _enabled

        try:
            _load_model()
            _enabled = True
            logger.info("困惑度模型加载成功。")
        except Exception as exc:
            logger.warning("困惑度模型加载失败，将跳过困惑度评估：%s", exc)
            _enabled = False

        return _enabled


def _load_model() -> None:
    global _model, _tokenizer, _device

    import torch  # type: ignore
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast  # type: ignore

    model_name = os.getenv("PERPLEXITY_MODEL", "uer/gpt2-chinese-cluecorpussmall")

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    _tokenizer = GPT2TokenizerFast.from_pretrained(model_name)
    _model = GPT2LMHeadModel.from_pretrained(model_name)
    _model.to(_device)
    _model.eval()

    logger.info("已加载困惑度模型：model=%s device=%s", model_name, _device)


def calc_perplexity(text: str) -> float | None:
    """
    计算文本在当前语言模型下的困惑度（perplexity）。
    数值越低，表示该模型越“熟悉”该文本。
    未启用或出错时返回 None。
    """
    if not text or not text.strip():
        return None

    if not is_enabled():
        return None

    import torch  # type: ignore

    try:
        encodings = _tokenizer(text, return_tensors="pt")
        input_ids = encodings["input_ids"].to(_device)

        max_length = getattr(_model.config, "n_positions", 1024)
        stride = 512

        seq_len = input_ids.size(1)
        nlls = []

        with torch.no_grad():
            for begin_loc in range(0, seq_len, stride):
                end_loc = min(begin_loc + max_length, seq_len)
                trg_len = end_loc - begin_loc

                input_ids_slice = input_ids[:, begin_loc:end_loc]
                target_ids = input_ids_slice.clone()

                outputs = _model(input_ids_slice, labels=target_ids)
                neg_log_likelihood = outputs.loss * trg_len
                nlls.append(neg_log_likelihood)

                if end_loc == seq_len:
                    break

        total_nll = torch.stack(nlls).sum()
        ppl = torch.exp(total_nll / seq_len)
        return float(ppl.item())

    except Exception as exc:
        logger.warning("困惑度计算异常：%s", exc)
        return None