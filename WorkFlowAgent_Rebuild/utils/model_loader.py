from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
import importlib.util
from huggingface_hub.constants import HF_HUB_CACHE
from threading import Thread
import gc

class ModelLoader:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.status = False

    def load_model(self, model_name: str):
        """
        model_id:
            username/repo_model_name -> remote (often)
            /home/ubuntu/.cache/huggingface/hub/repo_model_name/snapshot/<random_number_dir> -> local

        cache_dir:
            HF_HUB_CACHE -> default
            /home/ubuntu/bowei/huggingface_model_download/model_download/cache -> 指定
        To configure where repositories from the Hub will be cached locally (models, datasets and spaces).
        Defaults to "$HF_HOME/hub" (e.g. "~/.cache/huggingface/hub" by default).
        """
        print(f"正在載入模型：{model_name}")
        # model_id = "meta-llama/Llama-3.2-1B-Instruct"
        # model_id = "DiTy/gemma-2-9b-it-function-calling-GGUF"
        cache_dir = "/home/ubuntu/bowei/huggingface_model_download/model_download/cache"
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            # use float16 or float32 if bfloat16 is not available to you.
            torch_dtype=torch.bfloat16,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True),
            cache_dir=cache_dir,  # optional
            # gguf_file="gemma-2-9B-it-function-calling-Q5_K_M.gguf"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir,  # optional
            quantization_config=BitsAndBytesConfig(load_in_4bit=True),
            # gguf_file="gemma-2-9B-it-function-calling-Q5_K_M.gguf"
        )
        self.status = True

    def unload_model_and_tokenizer(self):
        """動態卸載模型與分詞器"""
        class UnloadThread(Thread):
            def __init__(self):
                Thread.__init__(self)

            def run(self):
                print("正在卸載模型與釋放資源")
                print("模型與分詞器已卸載")
                initial_memory = torch.cuda.memory_allocated()
                with torch.no_grad():
                    while True:
                        print("torch.cuda.max_memory_cached", torch.cuda.torch.cuda.memory_allocated())
                        print("torch.cuda.max_memory_reserved", torch.cuda.torch.cuda.memory_cached())
                        loader.model = None
                        loader.tokenizer = None
                        del loader.model
                        del loader.tokenizer
                        gc.collect()
                        torch.cuda.empty_cache()
                        torch.cuda.ipc_collect()
                        torch.cuda.reset_peak_memory_stats()
                        current_memory = torch.cuda.memory_allocated()
                        print("當前記憶體使用量:", current_memory)

                        if current_memory < initial_memory:
                            print("模型與分詞器已成功卸載")
                            break
                        else:
                            print("記憶體未完全釋放，繼續嘗試卸載...")

        unload_thread = UnloadThread()
        unload_thread.start()
        self.status = False

loader = ModelLoader()
