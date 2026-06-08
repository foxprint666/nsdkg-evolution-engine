# ==========================================
# Copyright (c) 2026
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==========================================

import os
from alibabacloud_tea_openapi.models import Config as OpenApiConfig
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_tea_util import models as util_models

class AliyunComputeCluster:
    """Manages scaling and secure execution configurations on Alibaba Cloud ECS."""

    def __init__(self, region_id: str = "cn-hangzhou"):
        self.region_id = region_id
        # Client initialized on demand to avoid errors if credentials aren't set
        self.client = None

    def create_ecs_client(self) -> EcsClient:
        access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

        if not access_key_id or not access_key_secret:
            raise ValueError("Credentials missing: ALIBABA_CLOUD_ACCESS_KEY_ID or SECRET is unset.")

        config = OpenApiConfig(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            region_id=self.region_id,
            endpoint=f"ecs.{self.region_id}.aliyuncs.com"
        )
        return EcsClient(config)

    def get_client(self):
        if not self.client:
            self.client = self.create_ecs_client()
        return self.client

    def verify_agent_cluster_status(self) -> dict:
        """Queries the active cluster to verify launched execution agents."""
        try:
            client = self.get_client()
            request = ecs_models.DescribeInstancesRequest(
                region_id=self.region_id,
                page_size=10
            )
            runtime = util_models.RuntimeOptions()
            response = client.describe_instances_with_options(request, runtime)

            instances = []
            for instance in response.body.instances.instance:
                instances.append({
                    "id": instance.instance_id,
                    "status": instance.status,
                    "type": instance.instance_type
                })
            print(f"[ECS] Cluster status verified successfully. Active instances: {len(instances)}")
            return {"status": "Success", "instances": instances}

        except Exception as err:
            print(f"[ECS ERROR] Failed to verify cluster status: {str(err)}")
            return {"status": "Error", "message": str(err)}

def dispatch_remote_sandbox(ecs_client: EcsClient, instance_id: str, region_id: str, script_path: str):
    """Executes a sandbox target remotely using Aliyun Cloud Assistant."""
    try:
        with open(script_path, "r") as f:
            script_content = f.read()

        command_request = ecs_models.RunCommandRequest(
            region_id=region_id,
            instance_id=[instance_id],
            type="RunShellScript",
            command_content=script_content,
            timeout=60
        )
        response = ecs_client.run_command(command_request)
        print(f"[ECS] Dispatched remote sandbox to {instance_id}. Invoke ID: {response.body.invoke_id}")
        return response.body.invoke_id
    except Exception as err:
        print(f"[ECS ERROR] Failed to dispatch remote sandbox: {str(err)}")
        return None
