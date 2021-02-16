h_formula_block(t, 0, 0, 0, 0, 0) :- fail.
v_formula_block(t, 0, 0, 0, 0, 0) :- fail.
match(0,0) :- fail.

col(Col) :- data_block(_, Col, _, _, _, _, _).
col(Col) :- data_block(_, _, _, Col, _, _, _).
row(Row) :- data_block(_, _, Row, _, _, _, _).
row(Row) :- data_block(_, _, _, _, Row, _, _).

col(Col) :- v_formula_block(_, _, Col, _, _, _).
col(Col) :- v_formula_block(_, _, _, Col, _, _).
row(Row) :- h_formula_block(_, _, Row, _, _, _).
row(Row) :- h_formula_block(_, _, _, Row, _, _).

:- table map/2.
map(X,XM) :- match(X,XM).
map(XM,XM) :- col(XM), \+ match(XM,_).
map(XM,XM) :- row(XM), \+ match(XM,_).
map(xindex(R,X),xindex(R,XM)) :- map(X,XM).
map(yindex(R,X),yindex(R,XM)) :- map(X,XM).

new_xindex(Old, -, Old).
new_yindex(Old, -, Old).
%new_xindex(Old, Relative, xindex(Relative, Old)) :- Relative \= -.
%new_yindex(Old, Relative, yindex(Relative, Old)) :- Relative \= -.
new_xindex(Old, Relative, xindex(Relative, Old)) :- dif(Relative, -).
new_yindex(Old, Relative, yindex(Relative, Old)) :- dif(Relative, -).

:- table block/8.
block(Id, X1o, Y1o, X2o, Y2o, W, H, dep(none,none,none)) :- data_block(Id, X1, Y1, X2, Y2, W, H), map(X1,X1o), map(Y1,Y1o), map(X2,X2o), map(Y2,Y2o).
block(Id, X1oo, Y1o, X2oo, Y2o, W, H, dep(D,RangeName,DD)) :-
                        h_formula_block(Id, Te, Y1, Y2, H, RelativePosition), range(Id, R, RangeName), depends(R, T), type(D, T), D\=Id,
                        block(D, X1, _, X2, _, W, _, DD), map(X1, X1o), map(Y1, Y1o), map( X2, X2o), map(Y2, Y2o),
                        new_xindex(X1o, RelativePosition, X1oo), new_xindex(X2o, RelativePosition, X2oo).
block(Id, X1o, Y1oo, X2o, Y2oo, W, H, dep(D,RangeName, DD)) :-
                        v_formula_block(Id, Te, X1, X2, W, RelativePosition), range(Id, R, RangeName), depends(R, T), type(D, T), D\=Id,
                        block(D, _, Y1, _, Y2, _, H, DD), map(X1, X1o), map(Y1, Y1o), map( X2, X2o), map(Y2, Y2o),
                        new_yindex(Y1o, RelativePosition, Y1oo), new_yindex(Y2o, RelativePosition, Y2oo).

output(Blocks) :- setof(oblock(Ids, X1, Y1, X2, Y2, W, H, S),
                         Dep^Iden^G^(block(Iden, X1, Y1, X2, Y2, W, H, Dep),
                                 setof([Id, D], X1^Y1^X2^Y2^W^H^block(Id, X1, Y1, X2, Y2, W, H, D), G),
                                maplist(nth0(1), G, S), maplist(nth0(0), G, Ids)),
                         Blocks).


type(B, T) :- raw_type(B, simple_type(T)).
type(B, comp_type(T, MI)) :- raw_type(B, comp_type(T, I)), map(I, MI).

depends(Range, Type) :- raw_depends(Range, simple_type(Type)).
depends(Range, comp_type(T, MI)) :- raw_depends(Range, comp_type(T, I)), map(I, MI).

