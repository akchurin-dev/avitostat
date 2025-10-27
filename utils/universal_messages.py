from typing import Literal
from typing import NamedTuple

from openai.types.responses import ResponseInputItemParam


INDENT = "\t"


class Message(NamedTuple):
    author: Literal["manager", "client"]
    text: str | None
    image_url: str | None

    @property
    def is_text(self) -> bool:
        return bool(self.text)

    @property
    def is_image(self) -> bool:
        return bool(self.image_url)

    @property
    def from_manager(self) -> bool:
        return self.author == "manager"

    @property
    def from_client(self) -> bool:
        return self.author == "client"

    @property
    def content(self) -> str:
        if self.text:
            return self.text

        if self.image_url:
            return self.image_url

        assert False

    def as_xml(
        self,
        author_as_tag: bool = True,
        message_tag: str = "Message",
        manager_tag: str = "Manager",
        client_tag: str = "Client",
        hide_image_url: bool = True,
        image_number: int = 0,
    ) -> str:

        if not author_as_tag:
            tag = message_tag
        elif self.from_client:
            tag = client_tag
        elif self.from_manager:
            tag = manager_tag
        else:
            assert False

        content = self.content
        if self.is_image and hide_image_url:
            content = "Изображение " + str(image_number)

        lines = content.split("\n")

        if len(lines) == 1:
            return f"<{tag}>{lines[0]}</{tag}>"

        return "<" + tag + ">\n" + _add_indent(content, 1) + "\n</" + tag + ">"

    def as_openai_format(self, image_number: int | None = None) -> ResponseInputItemParam:
        role: Literal["user", "assistant"] = "user"
        if self.from_manager:
            role = "assistant"

        if self.is_text:
            return {
                "role": role,
                "content": self.content,
            }

        if self.is_image:
            return {
                "role": role,
                "content": [
                    {
                        "type": "input_text",
                        "text": "Изображение " + str(image_number),
                    },
                    {
                        "type": "input_image",
                        "image_url": self.content,
                        "detail": "low",
                    },
                ],
            }

        assert False


def dialog_as_xml(
    messages: list[Message],
    hide_image_url: bool = True,
    author_as_tag: bool = True,
    dialog_tag: str = "Dialog",
    message_tag: str = "Message",
    manager_tag: str = "Manager",
    client_tag: str = "Client",
) -> str:

    xmls: list[str] = []
    images_count = 0

    for message in messages:
        if message.is_image:
            images_count += 1

        xmls.append(message.as_xml(
            author_as_tag=author_as_tag,
            message_tag=message_tag,
            manager_tag=manager_tag,
            client_tag=client_tag,
            hide_image_url=hide_image_url,
            image_number=images_count,
        ))

    return "\n".join([
        "<" + dialog_tag + ">",
        _add_indent("\n".join(xmls), 1),
        "</" + dialog_tag + ">",
    ])


def dialog_to_openai_images(messages: list[Message]) -> list[ResponseInputItemParam]:
    images_ai_input: list[ResponseInputItemParam] = []

    for message in messages:
        if not message.is_image:
            continue

        formatted_message = message.as_openai_format(len(images_ai_input))
        images_ai_input.append(formatted_message)

    return images_ai_input


def _add_indent(text: str, indents: int) -> str:
    indent = INDENT * indents
    return "\n".join(indent + line for line in text.split("\n"))
