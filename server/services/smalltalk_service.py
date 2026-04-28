from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmallTalkReply:
    reply: str
    keep_mic_open: bool = True


class SmallTalkService:
    """Fast local replies for common Thai small-talk turns during demos."""

    def get_reply(self, message: str) -> SmallTalkReply | None:
        normalized = self._normalize(message)
        if not normalized:
            return None

        if "หิว" in normalized:
            if any(keyword in normalized for keyword in ("กิน", "เมนู", "แนะนำ", "ข้าว")):
                return SmallTalkReply(
                    reply="ถ้าหิวข้าว ลองเริ่มจากข้าวกะเพรา ข้าวมันไก่ หรือโจ๊กอุ่น ๆ ก็ดีนะ ถ้าอยากได้แนวเผ็ด เบา ๆ หรือประหยัด เดี๋ยวช่วยเลือกต่อให้ได้",
                    keep_mic_open=True,
                )
            return SmallTalkReply(
                reply="ถ้าหิวลองหาอะไรรองท้องก่อนดีไหม หรืออยากให้ช่วยคิดเมนูง่าย ๆ ให้ก็ได้นะ",
                keep_mic_open=True,
            )
        if "ง่วง" in normalized:
            return SmallTalkReply(
                reply="ถ้าง่วงมากลองพักสายตาหรือยืดเส้นนิดหนึ่งก็ดีนะ อยากให้ช่วยชวนคุยต่อไหม",
                keep_mic_open=True,
            )
        if "เหนื่อย" in normalized:
            return SmallTalkReply(
                reply="วันนี้น่าจะเหนื่อยพอสมควรเลย ลองพักหายใจลึก ๆ ก่อนก็ได้นะ อยากคุยต่อไหม",
                keep_mic_open=True,
            )
        if "เบื่อ" in normalized:
            return SmallTalkReply(
                reply="งั้นลองเปลี่ยนอารมณ์กันนิดหนึ่งไหม อยากฟังข่าว ดูอากาศ หรือคุยเล่นต่อก็ได้",
                keep_mic_open=True,
            )
        if "เหงา" in normalized:
            return SmallTalkReply(
                reply="เราอยู่คุยเป็นเพื่อนได้นะ อยากชวนคุยเรื่องเบา ๆ หรือให้ช่วยอะไรต่อดี",
                keep_mic_open=True,
            )
        if "สวัสดี" in normalized or "หวัดดี" in normalized:
            return SmallTalkReply(
                reply="สวัสดี มีอะไรอยากให้ช่วยต่อไหม",
                keep_mic_open=True,
            )
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return "".join(text.casefold().split())


_smalltalk_service = SmallTalkService()


def get_smalltalk_service() -> SmallTalkService:
    return _smalltalk_service
