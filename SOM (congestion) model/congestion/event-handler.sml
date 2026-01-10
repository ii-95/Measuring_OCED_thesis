(* generic function for writing a list of strings to .csv *)

fun write_record(file_id, l) = 
let
   val file = TextIO.openAppend(file_id)
   val _ = TextIO.output(file, list2string(l))
   val _ = TextIO.output(file, "\n")
in
   TextIO.closeOut(file)
end;

(* write event to table "event" and respective event type table *)
fun write_event(event_id, et: EventType, ea_values: string list) = 
let
	val event_file_id = "./event.csv"
	val event_type_file_id = "./event_" ^ event_map_type(et) ^ ".csv"
	val time = t2s(Mtime())
	val _ = write_record(event_file_id, [event_id, et])
	val _ = write_record(event_type_file_id, [event_id,time]^^ea_values)
in
   event_id
end;

(* write qualified relations to table "object_object" *)
fun write_relations_recursively(file, []) = TextIO.closeOut(file) | 
write_relations_recursively(file, [obj_id1, obj_id2, qualifier]::qualified_pairs) = 
   (TextIO.output(file, list2string([obj_id1, obj_id2, qualifier]));
   TextIO.output(file, "\n");
   write_relations_recursively(file, qualified_pairs));

fun cartesian_single(_,[],_) = [] | cartesian_single(obj_id1, obj_id2::obj_ids, qualifier) = [obj_id1, obj_id2, qualifier]::cartesian_single(obj_id1, obj_ids, qualifier)

fun relationship_cartesian([],_,_) = [] | relationship_cartesian(obj_id1::obj_ids, obj_ids2, qualifier) = cartesian_single(obj_id1, obj_ids2, qualifier)^^relationship_cartesian(obj_ids, obj_ids2, qualifier)

fun write_e2o_relations(qualified_pairs) =
let
   val file = TextIO.openAppend("./event_object.csv")
in
   write_relations_recursively(file, qualified_pairs)
end;

fun write_o2o_relations(qualified_pairs) =
let
   val file = TextIO.openAppend("./object_object.csv")
in
   write_relations_recursively(file, qualified_pairs)
end;

(* write object to table "object" and respective object type table *)
fun initialize_objects_recursively(object_file, object_type_file, object_type, []) = 
	(TextIO.closeOut(object_file); TextIO.closeOut(object_type_file)) |
initialize_objects_recursively(object_file, object_type_file, object_type, (object_id)::object_ids) =
let
	val ocel_time = t2s(Mtime())
	val changed_field = ""
in
   (TextIO.output(object_file, list2string([object_id, object_type]));
   TextIO.output(object_file, "\n");
   TextIO.output(object_type_file, list2string([object_id, ocel_time, changed_field]));
   TextIO.output(object_type_file, "\n");  
   initialize_objects_recursively(object_file, object_type_file, object_type, object_ids))
end;

fun initialize_objects(object_type, object_ids) = 
let
   val object_file_id = "./object.csv"
   val object_type_file_id = "./object_" ^ object_map_type(object_type) ^ ".csv"
   val object_file = TextIO.openAppend(object_file_id)
   val object_type_file = TextIO.openAppend(object_type_file_id)
in
   initialize_objects_recursively(object_file, object_type_file, object_type, object_ids)
end;


(* object type specific functions *)
fun initialize_order((oid, items): Order) = 
let
   val object_ids = [oid]
in
   initialize_objects("orders", object_ids)
end;


fun initialize_items(its: Items) = initialize_objects("items", its)


fun write_place_order((oid, items): Order) =
let
   val event_id = "place_"^oid;
   (* e2o *)
   val event_order = [[event_id, oid, "order"]]
   val event_items = relationship_cartesian([event_id], items, "item")
   val e2o_relations = event_order^^event_items
   (* o2o *)
   val order_items = relationship_cartesian([oid], items, "contains")
   val o2o_relations = order_items
in
   (
   initialize_order((oid, items));
   initialize_items(items);
   write_event(event_id, "place order", []);
   write_e2o_relations(e2o_relations);
   write_o2o_relations(o2o_relations)
   )
end;

fun write_pick_item(item: Item)=
let
   val event_id = "pick_"^item;
   (* e2o *)
   val event_item = [[event_id, item, "item"]]
   val e2o_relations = event_item
in
   (
   write_event(event_id, "pick item", []);
   write_e2o_relations(e2o_relations)
   )
end;

fun write_ship_order((oid, items): Order) =
let
   val event_id = "ship_"^oid;
   (* e2o *)
   val event_order = [[event_id, oid, "order"]]
   val event_items = relationship_cartesian([event_id], items, "item")
   val e2o_relations = event_order^^event_items
   (* o2o *)
in
   (
   write_event(event_id, "ship order", []);
   write_e2o_relations(e2o_relations)
   )
end;