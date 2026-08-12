import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def actualize_amo_fields(account: amo.models.AmoAccount) -> None:
    tlogger = TraceLogger()
    tlogger.info(f"Actualize amo fields for {account.domain}")

    actualize_amo_entity_fields(account, amo_api.EntityEnum.LEADS, tlogger=tlogger)
    actualize_amo_entity_fields(account, amo_api.EntityEnum.CONTACTS, tlogger=tlogger)


def actualize_amo_entity_fields(account: amo.models.AmoAccount, entity: amo_api.EntityEnum, *, tlogger: TraceLogger) -> None:
    fields_in_amo = amo_api.get_fields(account, entity, tlogger=tlogger)

    db_entity: str
    if entity == amo_api.EntityEnum.LEADS:
        db_entity = amo.models.AmoEntity.LEAD  # type: ignore
    elif entity == amo_api.EntityEnum.CONTACTS:
        db_entity = amo.models.AmoEntity.CONTACT  # type: ignore
    else:
        error = f"Unexpected entity, got {entity}"
        tlogger.error(error)
        raise Exception(error)

    fields_in_db = list(amo.models.AmoField.get_fields_by_account(account.amo_id, db_entity))
    fields_ids_to_fields_in_amo: dict[int, amo_api.Field] = {field_in_amo.id: field_in_amo for field_in_amo in fields_in_amo}

    _update_existing_fields(fields_ids_to_fields_in_amo, fields_in_db)
    _delete_not_actual_fields(fields_ids_to_fields_in_amo, fields_in_db)
    _create_new_fields(account, fields_in_amo, fields_in_db, db_entity)

    fields_in_db = list(amo.models.AmoField.get_fields_by_account(account.amo_id, db_entity))
    _actualize_enums(fields_in_amo, fields_in_db)


def _delete_not_actual_fields(fields_ids_to_fields_in_amo: dict[int, amo_api.Field], fields_in_db: list[amo.models.AmoField]) -> None:
    fields_ids_for_delete: list[int] = []

    for field_in_db in fields_in_db:
        if field_in_db.amo_id not in fields_ids_to_fields_in_amo:
            fields_ids_for_delete.append(field_in_db.pk)

    amo.models.AmoField.objects.filter(id__in=fields_ids_for_delete).delete()


def _update_existing_fields(fields_ids_to_fields_in_amo: dict[int, amo_api.Field], fields_in_db: list[amo.models.AmoField]) -> None:
    updated_fields: list[amo.models.AmoField] = []

    for db_field in fields_in_db:
        amo_field = fields_ids_to_fields_in_amo.get(db_field.amo_id)

        if amo_field is None:
            continue

        updated = False

        if amo_field.name != db_field.name:
            db_field.name = amo_field.name
            updated = True

        if amo_field.type != db_field.type:
            db_field.type = amo_field.type
            updated = True

        if amo_field.code != db_field.code:
            db_field.code = amo_field.code
            updated = True

        if (amo_field.enums is not None) != db_field.enum:
            db_field.enum = amo_field.enums is not None
            updated = True

        if updated:
            updated_fields.append(db_field)

    amo.models.AmoField.objects.bulk_update(updated_fields, ["name", "type", "code", "enum"])


def _create_new_fields(
    account: amo.models.AmoAccount,
    fields_in_amo: list[amo_api.Field],
    fields_in_db: list[amo.models.AmoField],
    entity: str,
) -> None:

    fields_in_db_amo_ids: set[int] = {db_field.amo_id for db_field in fields_in_db}
    fields_for_create: list[amo.models.AmoField] = []

    for amo_field in fields_in_amo:
        if amo_field.id in fields_in_db_amo_ids:
            continue

        fields_for_create.append(amo.models.AmoField.create_instance(
            account_id=account.amo_id,
            amo_id=amo_field.id,
            entity=entity,
            name=amo_field.name,
            type=amo_field.type,
            code=amo_field.code,
            enum=amo_field.enums is not None,
        ))

    amo.models.AmoField.objects.bulk_create(fields_for_create)


def _actualize_enums(fields_in_amo: list[amo_api.Field], fields_in_db: list[amo.models.AmoField]) -> None:
    enums_in_amo: list[amo_api.FieldEnum] = [enum for amo_field in fields_in_amo for enum in amo_field.enums or []]
    enums_in_db = list(amo.models.AmoFieldEnum.objects.filter(field_id__in=[db_field.pk for db_field in fields_in_db]))

    enums_ids_to_enums_in_amo: dict[int, amo_api.FieldEnum] = {amo_enum.id: amo_enum for amo_enum in enums_in_amo}

    _update_existing_enums(enums_ids_to_enums_in_amo, enums_in_db)
    _delete_extra_enums(enums_ids_to_enums_in_amo, enums_in_db)
    _create_new_enums(fields_in_amo, enums_in_db, fields_in_db)


def _delete_extra_enums(enums_ids_to_enums_in_amo: dict[int, amo_api.FieldEnum], enums_in_db: list[amo.models.AmoFieldEnum]) -> None:
    enums_ids_for_delete: list[int] = []

    for db_enum in enums_in_db:
        if db_enum.amo_id not in enums_ids_to_enums_in_amo:
            enums_ids_for_delete.append(db_enum.pk)

    amo.models.AmoFieldEnum.objects.filter(id__in=enums_ids_for_delete).delete()


def _update_existing_enums(enums_ids_to_enums_in_amo: dict[int, amo_api.FieldEnum], enums_in_db: list[amo.models.AmoFieldEnum]) -> None:
    updated_enums: list[amo.models.AmoFieldEnum] = []

    for db_enum in enums_in_db:
        amo_enum = enums_ids_to_enums_in_amo.get(db_enum.amo_id)

        if amo_enum is None:
            continue

        updated = False

        if db_enum.sort != amo_enum.sort:
            db_enum.sort = amo_enum.sort
            updated = True

        if db_enum.value != amo_enum.value:
            db_enum.value = amo_enum.value
            updated = True

        if updated:
            updated_enums.append(db_enum)

    amo.models.AmoFieldEnum.objects.bulk_update(updated_enums, ["sort", "value"])


def _create_new_enums(
    fields_in_amo: list[amo_api.Field],
    enums_in_db: list[amo.models.AmoFieldEnum],
    fields_in_db: list[amo.models.AmoField],
) -> None:

    existing_enums_amo_ids: set[int] = {db_enum.amo_id for db_enum in enums_in_db}
    amo_ids_to_fields_in_db: dict[int, amo.models.AmoField] = {db_field.amo_id: db_field for db_field in fields_in_db}
    created_enums: list[amo.models.AmoFieldEnum] = []

    for amo_field in fields_in_amo:
        for amo_enum in amo_field.enums or []:
            if amo_enum.id in existing_enums_amo_ids:
                continue

            db_field = amo_ids_to_fields_in_db[amo_field.id]

            created_enums.append(amo.models.AmoFieldEnum.create_instance(
                field_id=db_field.pk,
                amo_id=amo_enum.id,
                sort=amo_enum.sort,
                value=amo_enum.value,
            ))

    amo.models.AmoFieldEnum.objects.bulk_create(created_enums)
