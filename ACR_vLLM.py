### Import Libraries
import gc
import os
import sys
import torch
import warnings
import pandas as pd
from tqdm import tqdm
from transformers import logging
from huggingface_hub import login
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from utils import acr_prompt, remove_diffs, myeval, acr_prompt_summary, load_qa_dataframe
from vllm.distributed.parallel_state import destroy_model_parallel

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
def test_prompt(test_set, language_type, use_summary):
    test_prompts = []
    
    for row in tqdm(range(len(test_set))):
        example = test_set.iloc[row]
        if use_summary:
            prompt = acr_prompt_summary.format(lang = language_type,
                                              code_snippet = remove_diffs(example.old),
                                              code_review = example.review,
                                              summary = example.summary)
        else:
            prompt = acr_prompt.format(lang = language_type, 
                               code_snippet = remove_diffs(example.old),
                               code_review = example.review) 
        test_prompts.append(prompt)
    return test_prompts

### Evaluation
def save_eval(gold, output):
    generated = "\n".join([line[2:] for line in output.text.split("\n")])
    result = myeval(gold, generated)
    record = [generated] + list(result)
    return pd.DataFrame([record], columns = ['generation', 'em', 'em_trim', 'em_no_space', 'em_no_comment'])

### Run Test
def main():
    login(token = sys.argv[1])
    language_type = sys.argv[2]
    lang = language_type.lower()
    use_summary = "--summary" in sys.argv
    model_name = sys.argv[3]
    model_name_short = model_name.split("/")[1]
    mcqa_set = load_qa_dataframe(use_summary = use_summary)
    mcqa_set = mcqa_set.loc[mcqa_set['lang'] == lang]
    results_root = os.environ.get("CRQA_RESULTS_DIR", "results")
    save_dir = f"{results_root}/acr/{lang}/acr_{lang}_{model_name_short}.pkl"
    
    # Import Model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    sampling_params = SamplingParams(temperature = 0,
                                    max_tokens = 512,
                                    stop = ["[/{lang}]".format(lang = language_type)])     
                               
    llm = LLM(model = model_name, tensor_parallel_size = torch.cuda.device_count(), max_model_len = 4000)
    
    # Run Inference
    test_prompts = test_prompt(mcqa_set, language_type, use_summary)
    outputs = llm.generate(test_prompts, sampling_params)
    
    # Save Results
    c_save = pd.DataFrame(columns = ['generation', 'em', 'em_trim', 'em_no_space', 'em_no_comment'])
    for row in tqdm(range(len(outputs))):
        gold = "\n".join([line[1:] for line in mcqa_set.iloc[row].new.split("\n")])
        c_save = pd.concat([c_save, save_eval(gold, outputs[row].outputs[0])])

    os.makedirs(os.path.dirname(save_dir), exist_ok=True)
    c_save.to_pickle(save_dir)
    
    # Output Results
    print("EM_TRIM: ", c_save.em.sum())
    print("EM_NO_SPACE: ", c_save.em_no_space.sum())
    print("EM__NO_COMMENT: ", c_save.em_no_comment.sum())
    
    # Release Cache
    destroy_model_parallel()
    # del llm.llm_engine.model_executor.driver_worker
    gc.collect()
    torch.cuda.empty_cache()
    
if __name__ == "__main__":
    main()
    