from typing import Dict, Set, List
import re
from openagents.mods import BaseMod as ModBase

PROJECT_CH_REGEX = re.compile(r"^project:(?P<pid>[^:]+):channel:(?P<ch>[^:]+)$")

class ProjectChannelsMod(ModBase):
    """
    Mod giúp quản lý nhiều channel theo từng project, dựng trên messaging có sẵn.
    Tạo/sửa/xóa channel, route message theo (project_id, channel_name), và kiểm soát quyền.
    """
    def __init__(self, ctx, config):
        super().__init__(ctx, config)
        self.autocreate_channels: List[str] = config.get("autocreate_channels", ["general"])
        self.max_channels_per_project: int = int(config.get("max_channels_per_project", 50))
        self.enforce_membership: bool = bool(config.get("enforce_membership", True))
        self.roles = config.get("roles", {})
        # bộ nhớ nhẹ trong RAM: { project_id: {channels:set(str), members:{role:set(agent_id)}} }
        self.state: Dict[str, Dict] = {}
    async def on_start(self):
        await self.ctx.subscribe("channel.message.posted", self.handle_channel_message)
        await self.ctx.subscribe("project.channel.create", self.handle_create_channel)
        await self.ctx.subscribe("project.channel.delete", self.handle_delete_channel)
        await self.ctx.subscribe("project.membership.update", self.handle_membership_update)
        await self.ctx.subscribe("project.init", self.handle_project_init)
    
    def _ensure_project(self, project_id: str):
        if project_id not in self.state:
            self.state[project_id] = {
                "channels": set(self.autocreate_channels),
                "members": { "owner": set(), "maintainer": set(), "member": set() }
            }
    def _has_perm(self, agent_id: str, project_id: str, action: str) -> bool:
        if not self.enforce_membership:
            return True
        roles_in_project = self.state.get(project_id, {}).get("members", {})
        for role, agents in roles_in_project.items():
            if agent_id in agents and action in set(self.roles.get(role, [])):
                return True
        return False

    async def handle_project_init(self, event):
        """
        data = { "project_id": "...", "owners": ["agent:alice"], "members": ["agent:bob"] }
        """
        pid = event.data["project_id"]
        self._ensure_project(pid)
        owners = event.data.get("owners", [])
        members = event.data.get("members", [])
        self.state[pid]["members"]["owner"].update(owners)
        self.state[pid]["members"]["member"].update(members)
        # Thông báo các channel mặc định đã sẵn sàng
        await self.ctx.publish(
            name="project.initialized",
            scope="NETWORK",
            data={"project_id": pid, "channels": sorted(self.state[pid]["channels"])}
        )
    
    async def handle_create_channel(self, event):
        """
        data = { "project_id": "...", "channel": "dev", "by": "agent:alice" }
        """
        pid = event.data["project_id"]
        ch = event.data["channel"]
        by = event.data.get("by", event.source)
        self._ensure_project(pid)
        if len(self.state[pid]["channels"]) >= self.max_channels_per_project:
            return  
        if not self._has_perm(by, pid, "create"):
            return
        self.state[pid]["channels"].add(ch)
        await self.ctx.publish(
            name="project.channel.created",
            scope="NETWORK",
            data={"project_id": pid, "channel": ch, "by": by}
        )

    async def handle_delete_channel(self, event):
        pid = event.data["project_id"]
        ch = event.data["channel"]
        by = event.data.get("by", event.source)
        if not self._has_perm(by, pid, "delete"):
            return
        if pid in self.state and ch in self.state[pid]["channels"]:
            self.state[pid]["channels"].remove(ch)
            await self.ctx.publish(
                name="project.channel.removed",
                scope="NETWORK",
                data={"project_id": pid, "channel": ch, "by": by}
            )

    async def handle_membership_update(self, event):
        """
        data = { "project_id":"...", "role":"maintainer", "add":["agent:..."], "remove":[...] }
        """
        pid = event.data["project_id"]
        role = event.data["role"]
        self._ensure_project(pid)
        add = set(event.data.get("add", []))
        rem = set(event.data.get("remove", []))
        self.state[pid]["members"].setdefault(role, set()).update(add)
        self.state[pid]["members"][role] -= rem

    async def handle_channel_message(self, event):
        """
        Nhận mọi channel message, kiểm tra có thuộc không gian project không.
        event.address có thể là 'project:<pid>:channel:<ch>' hoặc 'channel:<ch>'
        """
        address = getattr(event, "address", None) or event.data.get("address")
        if not address:
            return
        m = PROJECT_CH_REGEX.match(address)
        if not m:
            return  # không phải message theo schema project:... -> bỏ qua
        pid, ch = m.group("pid"), m.group("ch")
        self._ensure_project(pid)
        if ch not in self.state[pid]["channels"]:
            # tự tạo nếu chưa tồn tại (tùy chọn)
            if ch in self.autocreate_channels:
                self.state[pid]["channels"].add(ch)
            else:
                return
        # Kiểm tra quyền post
        sender = event.data.get("sender") or event.source
        if not self._has_perm(sender, pid, "post"):
            return
        # Re-publish với scope CHANNEL để chỉ ai subscribe kênh đó nhận
        await self.ctx.publish(
            name="project.channel.message.posted",
            scope="CHANNEL",
            channel=f"project:{pid}:channel:{ch}",
            data={
                "project_id": pid,
                "channel": ch,
                "sender": sender,
                "text": event.data.get("text"),
                "attachments": event.data.get("attachments", []),
                "ts": event.ts,
            }
        )

# entrypoint cho loader của OpenAgents
def register(ctx, config):
    return ProjectChannelsMod(ctx, config)