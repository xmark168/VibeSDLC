import argparse
import time
import torch
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"


def make_dummy_code(seq_len: int) -> str:
    """
    Tạo một đoạn 'code' giả có độ dài xấp xỉ seq_len ký tự.
    Chỉ để benchmark tương đối.
    """
    unit = "def foo(x):\n    return x * 2  # dummy code\n\n"
    text = (unit * (seq_len // len(unit) + 1))[:seq_len]
    return text


def mean_pooling(last_hidden_state: torch.Tensor,
                 attention_mask: torch.Tensor) -> torch.Tensor:
    """
    Jina v2 khuyến nghị dùng mean pooling để lấy embedding. 
    """
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


def benchmark(batch_size: int, seq_len: int, num_batches: int, max_length: int):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print(f"Loading tokenizer & model: {MODEL_NAME} ...")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
    )
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        dtype=torch.float16,
    ).to(device)
    model.eval()

    # Tạo batch text giả
    dummy_text = make_dummy_code(seq_len)
    texts = [dummy_text for _ in range(batch_size)]

    # Warmup
    print("Warming up 3 batches...")
    with torch.no_grad():
        for _ in range(3):
            enc = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(device)

            out = model(**enc)
            _ = mean_pooling(out.last_hidden_state, enc["attention_mask"])

        if device == "cuda":
            torch.cuda.synchronize()

    # Benchmark
    print("Start benchmark...")
    start = time.time()
    with torch.no_grad():
        for i in range(num_batches):
            enc = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(device)

            out = model(**enc)
            emb = mean_pooling(out.last_hidden_state, enc["attention_mask"])

            # ép compute xong (tránh lazy)
            _ = float(emb[0, 0])

            if device == "cuda":
                torch.cuda.synchronize()

            if (i + 1) % 10 == 0:
                print(f"  done batch {i + 1}/{num_batches}")

    end = time.time()

    total_time = end - start
    total_samples = batch_size * num_batches
    approx_tokens_per_sample = seq_len  # xấp xỉ
    total_tokens = approx_tokens_per_sample * total_samples

    print("\n===== RESULT =====")
    print(f"Model:                {MODEL_NAME}")
    print(f"Batch size:           {batch_size}")
    print(f"Seq length (chars~):  {seq_len}")
    print(f"Num batches:          {num_batches}")
    print(f"Total samples:        {total_samples}")
    print(f"Total time:           {total_time:.3f} s")
    print(f"Samples / second:     {total_samples / total_time:.2f}")
    print(f"Approx tokens / sec:  {total_tokens / total_time:.2f}")
    print("==================\n")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark jina-embeddings-v2-base-code throughput (no smart benchmarking)."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Số câu/code snippet mỗi batch.",
    )
    parser.add_argument(
        "--seq-len",
        type=int,
        default=512,
        help="Độ dài chuỗi (ký tự, xấp xỉ token).",
    )
    parser.add_argument(
        "--num-batches",
        type=int,
        default=100,
        help="Số batch để chạy benchmark.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=2048,
        help="max_length cho tokenizer/model (token).",
    )

    args = parser.parse_args()

    benchmark(
        batch_size=args.batch_size,
        seq_len=args.seq_len,
        num_batches=args.num_batches,
        max_length=args.max_length,
    )


if __name__ == "__main__":
    main()
