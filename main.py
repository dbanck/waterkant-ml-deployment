#!/usr/bin/env python
import os
from constructs import Construct
from cdktf import (
    App,
    AssetType,
    TerraformAsset,
    TerraformOutput,
    Fn,
    TerraformStack,
    TerraformVariable,
)
from cdktf_cdktf_provider_random.pet import Pet
from cdktf_cdktf_provider_random.provider import RandomProvider
from cdktf_cdktf_provider_google.provider import GoogleProvider
from cdktf_cdktf_provider_google.storage_bucket import StorageBucket
from cdktf_cdktf_provider_google.storage_bucket_object import StorageBucketObject
from cdktf_cdktf_provider_google.cloudfunctions2_function import (
    Cloudfunctions2Function,
    Cloudfunctions2FunctionBuildConfig,
    Cloudfunctions2FunctionBuildConfigSource,
    Cloudfunctions2FunctionBuildConfigSourceStorageSource,
    Cloudfunctions2FunctionServiceConfig,
)


class MyStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        project = TerraformVariable(
            self,
            "project",
            type="string",
            description="Google Cloud project id",
        )

        RandomProvider(
            self,
            "random-provider",
        )

        GoogleProvider(
            self,
            "google-provider",
            project=project.string_value,
            region="europe-west-1",
        )

        bucket_prefix = Pet(self, "bucket-prefix")
        bucket_name = bucket_prefix.id + "-ml-waterkant"
        bucket = StorageBucket(
            self,
            "bucket",
            name=bucket_name,
            location="EUROPE-WEST1",
            force_destroy=True,
            uniform_bucket_level_access=True,
        )

        code_asset = TerraformAsset(
            self,
            "code-asset",
            path=os.path.join(os.path.dirname(__file__), "..", "ml-project"),
            type=AssetType.ARCHIVE,
        )

        code = StorageBucketObject(
            self,
            "code",
            name=Fn.format("%s-%s.zip", ["ml-function", code_asset.asset_hash]),
            bucket=bucket.name,
            source=code_asset.path,
        )

        model_bucket_prefix = Pet(self, "model-bucket-prefix")
        model_bucket_name = model_bucket_prefix.id + "-ml-model"
        model_bucket = StorageBucket(
            self,
            "model-bucket",
            name=model_bucket_name,
            location="EUROPE-WEST1",
            force_destroy=True,
            uniform_bucket_level_access=True,
        )

        func = Cloudfunctions2Function(
            self,
            "func",
            name="ml-function",
            location="europe-west1",
            description="API for ML model",
            build_config=Cloudfunctions2FunctionBuildConfig(
                runtime="python311",
                entry_point="predict_external",
                source=Cloudfunctions2FunctionBuildConfigSource(
                    storage_source=Cloudfunctions2FunctionBuildConfigSourceStorageSource(
                        bucket=bucket.name,
                        object=code.output_name,
                    )
                ),
            ),
            service_config=Cloudfunctions2FunctionServiceConfig(
                available_memory="8Gi",
                available_cpu="4",
                max_instance_count=1,
                timeout_seconds=600,
                environment_variables={
                    "MODEL_BUCKET": model_bucket.name,
                    "MODEL_FOLDER": "bert",
                },
            ),
        )

        TerraformOutput(self, "function_uri", value=func.service_config.uri)


app = App()
MyStack(app, "ml-deployment")

app.synth()
