### Import Libraries
import gc
import os
import sys

# Fix for MIG (Multi-Instance GPU) UUID issue on cloud servers
cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
if cuda_visible.startswith("MIG-"):
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
import warnings
import itertools
import pandas as pd
from tqdm import tqdm
from transformers import logging
from huggingface_hub import login
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from vllm.sampling_params import GuidedDecodingParams
from vllm.distributed.parallel_state import destroy_model_parallel
from utils import si_prompt, ct_formatter, remove_diffs, count_matching_elements, calc_results, si_prompt_summary, load_qa_dataframe

### Silent Logging
logging.set_verbosity_error()
warnings.filterwarnings("ignore")


def check_gpu_memory(min_free_gb=3.5, gpu_memory_utilization=0.80):
    free, total = torch.cuda.mem_get_info()
    free_gb, total_gb = free / 1024**3, total / 1024**3
    needed_gb = max(min_free_gb, gpu_memory_utilization * total_gb)
    if free_gb < needed_gb:
        raise SystemExit(
            f"Not enough free GPU memory: {free_gb:.2f} GiB free / "
            f"{total_gb:.2f} GiB total (need >= {needed_gb:.2f} GiB). "
            "Another *_vLLM.py job or a Windows app is likely using the GPU.\n"
            "  1) Run `nvidia-smi` to see what is using the GPU\n"
            "  2) Kill leftover jobs: `pkill -9 -f vllm`\n"
            "  3) Run only ONE *_vLLM.py job at a time on this 6 GB GPU\n"
            "  4) Close heavy Windows apps (browser video, games) to free VRAM\n"
            "Then rerun this command."
        )

### Prompt Constructor
def prompt_combinations(example, mode, language_type, use_summary):
    symbol_index_map = {0:'A', 1:'B', 2:'C', 3:'D'}
    
    if mode == "easy":
        options = list(example.solution_wrong_easy)
    elif mode == "hard":
        options = list(example.solution_wrong_hard)

    options.append(example.solution_correct)
    all_permutations = list(itertools.permutations(options))
    
    prompts = []
    correct_symbols = []
    for permutation in all_permutations:
        correct_symbols.append(symbol_index_map[permutation.index(example.solution_correct)])
        if use_summary:
            prompts.append(si_prompt_summary.format(lang = language_type, 
                                                   option_a = "\n" + permutation[0],
                                                   option_b = "\n" + permutation[1],
                                                   option_c = "\n" + permutation[2],
                                                   option_d = "\n" + permutation[3],
                                                   code_snippet = remove_diffs(example.old),
                                                   code_review = example.review,
                                                   summary = example.summary,
                                                   ct = ct_formatter[example.type_correct]))
        else:
             prompts.append(si_prompt.format(lang = language_type, 
                                 option_a = "\n" + permutation[0],
                                 option_b = "\n" + permutation[1],
                                 option_c = "\n" + permutation[2],
                                 option_d = "\n" + permutation[3],
                                 code_snippet = remove_diffs(example.old),
                                 code_review = example.review,
                                 ct = ct_formatter[example.type_correct]))
    return prompts, correct_symbols, all_permutations

### Evaluation
def test_example(example, tokenizer, llm, sampling_params, mode, language_type, use_summary):
    symbols = ["A", "B", "C", "D"]
    symbol_ids = tokenizer.convert_tokens_to_ids(symbols)
    symbol_id_map = dict(zip(symbol_ids, symbols))

    prompt_permutations, correct_answers, combinations = prompt_combinations(example, mode, language_type, use_summary)
    model_answers = []

    output = llm.generate(prompt_permutations, sampling_params)
    for permutation in output:
    
        if len(permutation.outputs[0].logprobs) > 0:
            logprobs = permutation.outputs[0].logprobs[0]
        else:
            logprobs = []
        
        symbol_probs = []
        for symbol_id in symbol_id_map.keys():
            if symbol_id in logprobs:
                symbol_probs.append((logprobs[symbol_id].decoded_token, 
                                     logprobs[symbol_id].logprob))
            else:
                symbol_probs.append((symbol_id_map[symbol_id], 
                                     -9999))

        model_answers.append(dict(symbol_probs))
        
    example_record = [combinations, 
                model_answers, 
                [max(symbol_probs, key = symbol_probs.get) for symbol_probs in model_answers],
                correct_answers,
                example.type_correct]

    return pd.DataFrame([example_record], columns = ['combinations', 'softmax_probs', 'model_answers', 'correct_answers','GT'])

### Run Test
def main():
    login(token = sys.argv[1])
    language_type = sys.argv[2]
    lang = language_type.lower()
    mode = sys.argv[3]
    model_name = sys.argv[4]
    model_name_short = model_name.split("/")[1]
    use_summary = "--summary" in sys.argv
    mcqa_set = load_qa_dataframe(use_summary = use_summary)
    mcqa_set = mcqa_set.loc[mcqa_set['lang'] == lang]
    results_root = os.environ.get("CRQA_RESULTS_DIR", "results")
    save_dir = f"{results_root}/si/{lang}/{mode}/si_{mode}_{lang}_{model_name_short}.pkl"
    
    # Import Model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    guided_decoding_params = GuidedDecodingParams(choice = ["A", "B", "C", "D"])
    sampling_params = SamplingParams(temperature = 0,
                                    max_tokens = 512,
                                    logprobs = 20,
                                    guided_decoding = guided_decoding_params)
    
    
    check_gpu_memory(gpu_memory_utilization = 0.80)
    llm = LLM(model = model_name, tensor_parallel_size = torch.cuda.device_count(), max_model_len = 4000, gpu_memory_utilization = 0.80)

    # Run Inference
    c_save = pd.DataFrame(columns = ['combinations', 'softmax_probs', 'model_answers', 'correct_answers','GT'])
    for row in tqdm(range(len(mcqa_set))):
        if mcqa_set.iloc[row].type_correct != "remove_only":
            example_save = test_example(mcqa_set.iloc[row], tokenizer, llm, sampling_params, mode, language_type, use_summary)
            c_save = pd.concat([c_save, example_save])
    
    # Save and Output Results
    os.makedirs(os.path.dirname(save_dir), exist_ok=True)
    c_save.to_pickle(save_dir)
    results = pd.read_pickle(save_dir)
    calc_results(results)
    
    # Release Cache
    destroy_model_parallel()
    # del llm.llm_engine.model_executor.driver_worker
    gc.collect()
    torch.cuda.empty_cache()

if __name__ == "__main__":
    main()
