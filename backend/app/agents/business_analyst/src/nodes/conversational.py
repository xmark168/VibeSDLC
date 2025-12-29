import logging

from langchain_core.messages import HumanMessage, SystemMessage

from ..state import BAState
from .utils import _cfg, _sys_prompt, _user_prompt, _default_llm

logger = logging.getLogger(__name__)

async def respond_conversational(state: BAState, agent=None) -> dict:
    """Node: Respond to casual conversation (greetings, thanks, etc.)."""
    logger.info(f"[BA] Handling conversational message: {state['user_message'][:50]}...")
    
    try:
        system_prompt = _sys_prompt(agent, "respond_conversational")
        user_prompt = _user_prompt(
            "respond_conversational",
            user_message=state["user_message"]
        )
        
        response = await _default_llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config=_cfg(state, "respond_conversational")
        )
        
        message = response.content.strip()
        
        # Send response to user
        if agent:
            await agent.message_user("response", message)
            # Note: Removed redundant warning about attachments - the main response should address document context
        
        logger.info(f"[BA] Conversational response sent: {message[:50]}...")
        
        return {"is_complete": True}
        
    except Exception as e:
        logger.error(f"[BA] Conversational response failed: {e}")
        fallback = "Chào bạn! Mình là BA, sẵn sàng hỗ trợ. Bạn cần gì nhé? 😊"
        if agent:
            await agent.message_user("response", fallback)
        return {"is_complete": True}




