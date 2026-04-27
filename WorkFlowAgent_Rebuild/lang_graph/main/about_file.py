# NEW FETURE: 新增上傳plugin機制
dynamic_functions_google_schema = []
dynamic_functions = {}


from torch import Tensor
from PIL.Image import Image
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PydanticDeprecationWarning,
    SkipValidation,
    ValidationError,
    model_validator,
    validate_arguments,
)
from typing import (
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)
from collections.abc import Sequence
import inspect
from inspect import isfunction
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, get_args, get_origin, get_type_hints
import re
import json
import os
import importlib.util
import time
import types

# Extracts the initial segment of the docstring, containing the function description
description_re = re.compile(
    r"^(.*?)[\n\s]*(Args:|Returns:|Raises:|\Z)", re.DOTALL)
# Extracts the Args: block from the docstring
args_re = re.compile(
    r"\n\s*Args:\n\s*(.*?)[\n\s]*(Returns:|Raises:|\Z)", re.DOTALL)
# Splits the Args: block into individual arguments
args_split_re = re.compile(
    r"""
(?:^|\n)  # Match the start of the args block, or a newline
\s*(\w+):\s*  # Capture the argument name and strip spacing
(.*?)\s*  # Capture the argument description, which can span multiple lines, and strip trailing spacing
(?=\n\s*\w+:|\Z)  # Stop when you hit the next argument or the end of the block
""",
    re.DOTALL | re.VERBOSE,
)
# Extracts the Returns: block from the docstring, if present. Note that most chat templates ignore the return type/doc!
returns_re = re.compile(
    r"\n\s*Returns:\n\s*(.*?)[\n\s]*(Raises:|\Z)", re.DOTALL)

# if is_vision_available():

# if is_torch_available():


class TypeHintParsingException(Exception):
    """Exception raised for errors in parsing type hints to generate JSON schemas"""

    pass


class DocstringParsingException(Exception):
    """Exception raised for errors in parsing docstrings to generate JSON schemas"""

    pass


def _get_json_schema_type(param_type: str) -> Dict[str, str]:
    type_mapping = {
        int: {"type": "integer"},
        float: {"type": "number"},
        str: {"type": "string"},
        bool: {"type": "boolean"},
        Any: {},
    }
    # 不管有沒有套件都加入，這個function，主要是判斷影音跟圖片能不能run
    # if is_vision_available():
    type_mapping[Image] = {"type": "image"}
    # if is_torch_available():
    type_mapping[Tensor] = {"type": "audio"}
    return type_mapping.get(param_type, {"type": "object"})


def _parse_type_hint(hint: str) -> Dict:
    print("hint", hint)
    origin = get_origin(hint)
    print("origin", origin)
    args = get_args(hint)
    print("args", args)

    if origin is None:
        try:
            return _get_json_schema_type(hint)
        except KeyError:
            raise TypeHintParsingException(
                "Couldn't parse this type hint, likely due to a custom class or object: ", hint
            )

    elif origin is Union:
        # Recurse into each of the subtypes in the Union, except None, which is handled separately at the end
        subtypes = [_parse_type_hint(t) for t in args if t is not type(None)]
        if len(subtypes) == 1:
            # A single non-null type can be expressed directly
            return_dict = subtypes[0]
        elif all(isinstance(subtype["type"], str) for subtype in subtypes):
            # A union of basic types can be expressed as a list in the schema
            return_dict = {"type": sorted(
                [subtype["type"] for subtype in subtypes])}
        else:
            # A union of more complex types requires "anyOf"
            return_dict = {"anyOf": subtypes}
        if type(None) in args:
            return_dict["nullable"] = True
        return return_dict

    elif origin is list:
        if not args:
            return {"type": "array"}
        else:
            # Lists can only have a single type argument, so recurse into it
            return {"type": "array", "items": _parse_type_hint(args[0])}

    elif origin is tuple:
        if not args:
            return {"type": "array"}
        if len(args) == 1:
            raise TypeHintParsingException(
                f"The type hint {str(hint).replace('typing.', '')} is a Tuple with a single element, which "
                "we do not automatically convert to JSON schema as it is rarely necessary. If this input can contain "
                "more than one element, we recommend "
                "using a List[] type instead, or if it really is a single element, remove the Tuple[] wrapper and just "
                "pass the element directly."
            )
        if ... in args:
            raise TypeHintParsingException(
                "Conversion of '...' is not supported in Tuple type hints. "
                "Use List[] types for variable-length"
                " inputs instead."
            )
        return {"type": "array", "prefixItems": [_parse_type_hint(t) for t in args]}

    elif origin is dict:
        # The JSON equivalent to a dict is 'object', which mandates that all keys are strings
        # However, we can specify the type of the dict values with "additionalProperties"
        out = {"type": "object"}
        if len(args) == 2:
            out["additionalProperties"] = _parse_type_hint(args[1])
        return out

    raise TypeHintParsingException(
        "Couldn't parse this type hint, likely due to a custom class or object: ", hint)


def parse_google_format_docstring(docstring: str) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """
    Parses a Google-style docstring to extract the function description,
    argument descriptions, and return description.

    Args:
        docstring (str): The docstring to parse.

    Returns:
        The function description, arguments, and return description.
    """

    # Extract the sections
    description_match = description_re.search(docstring)
    args_match = args_re.search(docstring)
    returns_match = returns_re.search(docstring)

    # Clean and store the sections
    description = description_match.group(
        1).strip() if description_match else None
    docstring_args = args_match.group(1).strip() if args_match else None
    returns = returns_match.group(1).strip() if returns_match else None

    # Parsing the arguments into a dictionary
    if docstring_args is not None:
        docstring_args = "\n".join([line for line in docstring_args.split(
            "\n") if line.strip()])  # Remove blank lines
        matches = args_split_re.findall(docstring_args)
        args_dict = {match[0]: re.sub(
            r"\s*\n+\s*", " ", match[1].strip()) for match in matches}
    else:
        args_dict = {}

    return description, args_dict, returns


def _convert_type_hints_to_json_schema(func: Callable) -> Dict:
    # type_hints {'location': <class 'str'>, 'days': <class 'str'>, 'return': <class 'list'>}
    type_hints = get_type_hints(func)
    # signature (location: str, days: str) -> list
    signature = inspect.signature(func)
    required = []
    """
    signature.parameters.items() =>
    location, location: str
    days, days: str
    """
    for param_name, param in signature.parameters.items():
        if param.annotation == inspect.Parameter.empty:
            raise TypeHintParsingException(
                f"Argument {param.name} is missing a type hint in function {func.__name__}")
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    properties = {}
    for param_name, param_type in type_hints.items():
        properties[param_name] = _parse_type_hint(param_type)

    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required

    return schema


def get_json_schema(func: Callable) -> Dict:
    """
    此段程式碼使用 inspect.getdoc 獲取 func 的 docstring（即函數的說明文字），
    以進行參數和返回值的說明。如果 func 沒有 docstring，
    則拋出 DocstringParsingException 錯誤，提示說明不足，
    無法生成 JSON schema。doc.strip() 用來去除空白字符。
    """
    print("func", func)
    """
    doc =>
    Returns weather information based on the provided request.

    Args:
        location: The city to get the weather for.
        days: The number of days for the weather forecast (e.g. 1).

    Returns:
        list: A list of flight information dictionaries matching the request criteria.
    """
    doc = inspect.getdoc(func)
    print("doc", doc)
    if not doc:
        raise DocstringParsingException(
            f"Cannot generate JSON schema for {func.__name__} because it has no docstring!"
        )
    doc = doc.strip()
    """
    透過google的註解格式, parse 描述、參數、return出來
    """
    main_doc, param_descriptions, return_doc = parse_google_format_docstring(
        doc)

    json_schema = _convert_type_hints_to_json_schema(func)
    if (return_dict := json_schema["properties"].pop("return", None)) is not None:
        if return_doc is not None:  # We allow a missing return docstring since most templates ignore it
            return_dict["description"] = return_doc
    for arg, schema in json_schema["properties"].items():
        if arg not in param_descriptions:
            raise DocstringParsingException(
                f"Cannot generate JSON schema for {func.__name__} because the docstring has no description for the argument '{arg}'"
            )
        desc = param_descriptions[arg]
        enum_choices = re.search(
            r"\(choices:\s*(.*?)\)\s*$", desc, flags=re.IGNORECASE)
        if enum_choices:
            schema["enum"] = [c.strip()
                              for c in json.loads(enum_choices.group(1))]
            desc = enum_choices.string[: enum_choices.start()].strip()
        schema["description"] = desc

    output = {"name": func.__name__,
              "description": main_doc, "parameters": json_schema}
    if return_dict is not None:
        output["return"] = return_dict
    return {"type": "function", "function": output}


def create_schema_from_function(tool):
    # We accept either JSON schemas or functions for tools. If we get functions, we convert them to schemas
    print("tools", tool)
    if tool is not None:
        # tool_schemas = []
        # for tool in tools:
        if isinstance(tool, dict):
            # tool_schemas.append(tool)
            return tool
        elif isfunction(tool):
            # tool_schemas.append(get_json_schema(tool))
            result = get_json_schema(tool)
            return result
        else:
            raise ValueError(
                "Tools should either be a JSON schema, or a callable function with type hints "
                "and a docstring suitable for auto-conversion to a schema."
            )
    else:
        tool_schemas = None
    
def upload_tools_files(files):
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~in upload file~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    try:
        # print("upload_tools", files)
        # 讀取本地文件
        for file_path in files:
            # 讀取本地文件
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            spec = importlib.util.spec_from_file_location(file_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and isinstance(attr, types.FunctionType):
                    schema = create_schema_from_function(attr)
                    dynamic_functions_google_schema.append(schema)
                    dynamic_functions[attr_name] = attr
        print("======================= dynamic_functions_google_schema ==================================")
        print(dynamic_functions_google_schema)
        # for uploaded_file in files:
        #     file_path = f"/home/ubuntu/bowei/systex-local-rag-system-poc/backend/tools/{uploaded_file.filename}"
        #     with open(file_path, "wb") as buffer:
        #         buffer.write(uploaded_file.file.read())
        #     file_name = os.path.splitext(uploaded_file.filename)[0]
        #     spec = importlib.util.spec_from_file_location(file_name, file_path)
        #     module = importlib.util.module_from_spec(spec)
        #     spec.loader.exec_module(module)
        #     for attr_name in dir(module):
        #         attr = getattr(module, attr_name)
        #         if callable(attr) and isinstance(attr, types.FunctionType):
        #             schema = create_schema_from_function(attr)
        #             dynamic_functions_google_schema.append(schema)
        #             dynamic_functions[attr_name] = attr
    except Exception as e:
        print("upload_tools_ERROR\n", e)
_HERE = os.path.dirname(__file__)
file_path = [os.path.join(_HERE, "tools.py")]
# with open(file_path, 'rb') as file:
#     upload_file(file)
upload_tools_files(file_path)