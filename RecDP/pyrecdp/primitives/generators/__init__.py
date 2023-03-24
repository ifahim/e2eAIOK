from .binned import BinnedFeatureGenerator
from .category import CategoryFeatureGenerator
from .datetime import DatetimeFeatureGenerator
from .drop import DropUselessFeatureGenerator
from .name import RenameFeatureGenerator
from .fillna import FillNaFeatureGenerator
from .statics import StatisticsFeatureGenerator
from .type import TypeInferFeatureGenerator, TypeCheckFeatureGenerator,TypeConvertFeatureGenerator
from .nlp import DecodedTextFeatureGenerator, TextFeatureGenerator
from .geograph import GeoFeatureGenerator, CoordinatesInferFeatureGenerator
from .relation import RelationalFeatureGenerator
from .encode import OneHotFeatureGenerator, ListOneHotFeatureGenerator, TargetEncodeFeatureGenerator, LabelEncodeFeatureGenerator
from .feature_transform import ConvertToNumberFeatureGenerator

feature_infer_list = [
    TypeInferFeatureGenerator,   
]

relation_builder_list = [
    RelationalFeatureGenerator
]

label_feature_generator_list = [
    FillNaFeatureGenerator,
    RenameFeatureGenerator,
    TypeConvertFeatureGenerator,
    LabelEncodeFeatureGenerator,
]

pre_feature_generator_list = [
    CoordinatesInferFeatureGenerator,
    ConvertToNumberFeatureGenerator,
    FillNaFeatureGenerator,
    RenameFeatureGenerator
]

transformation_generator_list = [
    DecodedTextFeatureGenerator,
    DatetimeFeatureGenerator,
    GeoFeatureGenerator,
    TextFeatureGenerator,
]

index_generator_list = [
    BinnedFeatureGenerator,
    CategoryFeatureGenerator,
]

encode_generator_list = [
    OneHotFeatureGenerator,
    ListOneHotFeatureGenerator,
    #TargetEncodeFeatureGenerator
]

pre_enocode_feature_generator_list = [
    DropUselessFeatureGenerator,
]

post_feature_generator_list = [
    RenameFeatureGenerator
]

final_generator_list = [
    TypeCheckFeatureGenerator,
    DropUselessFeatureGenerator,
    TypeConvertFeatureGenerator,
]